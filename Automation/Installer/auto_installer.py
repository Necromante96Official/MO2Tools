# Auto-Installer robusto para MO2Tools v0.1.3
import os
import queue
import time
import logging
from logging.handlers import RotatingFileHandler
import re
import zipfile
from typing import Any, Dict, List, Optional, Set

try:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import (
        QApplication,
        QAbstractButton,
        QComboBox,
        QDialogButtonBox,
        QMessageBox,
        QPushButton,
        QRadioButton,
    )
except ImportError:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import (
        QApplication,
        QAbstractButton,
        QComboBox,
        QDialogButtonBox,
        QMessageBox,
        QPushButton,
        QRadioButton,
    )

_logger = logging.getLogger("MO2Tools.Installer")
_logger.setLevel(logging.DEBUG)


def _default_log_path() -> str:
    plugin_root = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", ".."))
    return os.path.join(plugin_root, "Logs", "mo2tools_installer.log")


def _ensure_file_logging() -> str:
    target_path = _default_log_path()
    target_norm = _norm_path(target_path)

    for handler in _logger.handlers:
        base_filename = getattr(handler, "baseFilename", None)
        if base_filename and _norm_path(str(base_filename)) == target_norm:
            return target_path

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    rotating = RotatingFileHandler(
        target_path,
        maxBytes=1_024_000,
        backupCount=3,
        encoding="utf-8",
    )
    rotating.setLevel(logging.DEBUG)
    rotating.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(rotating)
    return target_path


def _norm_path(path_value: str) -> str:
    return os.path.normcase(os.path.normpath(str(path_value).strip()))


def _sanitize_mod_name_from_archive(archive_path: str) -> str:
    name = os.path.splitext(os.path.basename(archive_path))[0]

    # Remove sufixo de metadados do Nexus (ex.: -1915-2-9-1-1773542770)
    name = re.sub(r"[-_]?\d+(?:[-_]\d+){2,}$", "", name)

    # Remove versões no padrão semântico (ex.: 2.9.1, v1.4.3, 1-2-0)
    name = re.sub(r"\b[vV]?\d+(?:[._-]\d+){1,4}(?:[a-zA-Z]\d*)?\b", "", name)

    # Remove tags comuns de release
    name = re.sub(r"\b(alpha|beta|rc|release|final|hotfix|build)\b",
                  "", name, flags=re.IGNORECASE)

    # Normaliza separadores
    name = re.sub(r"[._-]+", " ", name)
    name = re.sub(r"\s+", " ", name).strip(" -_.")

    if not name:
        fallback = os.path.splitext(os.path.basename(archive_path))[0].strip()
        return fallback or "Mod"

    return name


def _title_case_mod_name(name: str) -> str:
    known_tokens = {
        "smapi": "SMAPI",
        "api": "API",
        "ui": "UI",
        "dll": "DLL",
    }
    known_phrases = {
        "content patcher": "Content Patcher",
    }

    normalized = (name or "").strip()
    if not normalized:
        return "Mod"

    phrase_key = normalized.lower()
    if phrase_key in known_phrases:
        return known_phrases[phrase_key]

    words: List[str] = []
    for token in normalized.split(" "):
        clean = token.strip()
        if not clean:
            continue

        lowered = clean.lower()
        if lowered in known_tokens:
            words.append(known_tokens[lowered])
            continue

        if clean.isupper():
            words.append(clean)
            continue

        if any(ch.isdigit() for ch in clean):
            words.append(clean)
            continue

        words.append(clean[:1].upper() + clean[1:].lower())

    return " ".join(words) if words else "Mod"


class EnhancedAutoInstaller:
    def __init__(self, organizer: Any) -> None:
        self._organizer = organizer
        self._download_manager = organizer.downloadManager() if organizer else None
        self._session_started_at = time.time()
        self._log_file_path = _ensure_file_logging()

        self._install_queue: "queue.Queue[str]" = queue.Queue()
        self._installing = False

        self._pending_install_paths: Set[str] = set()
        self._inflight_install_paths: Set[str] = set()
        self._recent_install_paths: Dict[str, float] = {}
        self._recent_download_ids: Dict[int, float] = {}
        self._download_retry_counts: Dict[int, int] = {}
        self._download_id_by_path: Dict[str, int] = {}
        self._installed_events_by_path: Dict[str, float] = {}
        self._installed_events_by_name: Dict[str, float] = {}

        self._install_dedupe_ttl_seconds = 240.0
        self._download_dedupe_ttl_seconds = 360.0
        self._installed_event_ttl_seconds = 600.0
        self._download_retry_delay_ms_base = 1200

        self._active_dialog_timers: List[QTimer] = []
        self._manual_install_items: List[Dict[str, str]] = []

        self._download_hook_registered = False
        _logger.info(
            "Inicializando AutoInstaller | log=%s | hasOrganizer=%s | hasDownloadManager=%s",
            self._log_file_path,
            bool(self._organizer),
            bool(self._download_manager),
        )
        if self._download_manager:
            try:
                self._download_manager.onDownloadComplete(
                    self._safe_on_download_complete)
                self._download_hook_registered = True
                _logger.info("Hook de download registrado com sucesso.")
            except Exception as exc:
                _logger.warning(f"Falha ao conectar onDownloadComplete: {exc}")

        try:
            if self._organizer:
                self._organizer.modList().onModInstalled(self._record_install_event)
        except Exception as exc:
            _logger.warning(f"Falha ao conectar onModInstalled: {exc}")

    def _get_bool(self, key: str, default: bool) -> bool:
        if not self._organizer:
            return default
        try:
            value = self._organizer.pluginSetting("MO2Tools", key)
        except Exception:
            return default

        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "sim"}
        return default

    def _get_int(self, key: str, default: int) -> int:
        if not self._organizer:
            return default
        try:
            value = self._organizer.pluginSetting("MO2Tools", key)
        except Exception:
            return default

        try:
            parsed = int(value)
            return parsed if parsed > 0 else default
        except Exception:
            return default

    def _safe_on_download_complete(self, download_id: int) -> None:
        try:
            self._on_download_complete(download_id)
        except Exception as exc:
            _logger.exception(
                f"Exceção no callback de download {download_id}: {exc}")

    def _on_download_complete(self, download_id: int) -> None:
        self._try_handle_download_complete(download_id, dedupe_event=True)

    def _try_handle_download_complete(self, download_id: int, dedupe_event: bool) -> None:
        if not self._get_bool("enabled", True):
            _logger.debug("AutoInstall ignorado: plugin desabilitado")
            return
        if not self._get_bool("autoInstall", True):
            _logger.debug("AutoInstall ignorado: autoInstall desabilitado")
            return
        if not self._download_manager:
            _logger.debug(
                "AutoInstall ignorado: download manager indisponível")
            return

        _logger.debug(
            "Processando download completo | id=%s | dedupeEvent=%s",
            int(download_id),
            bool(dedupe_event),
        )

        if dedupe_event and self._is_duplicate_download_event(download_id):
            _logger.debug(
                "Evento de download duplicado ignorado | id=%s", int(download_id))
            return

        try:
            archive_path = self._download_manager.downloadPath(download_id)
        except Exception as exc:
            _logger.warning(
                f"Falha ao obter caminho do download {download_id}: {exc}")
            self._schedule_download_retry(
                int(download_id), "Falha ao obter caminho do download")
            return

        if not archive_path:
            self._schedule_download_retry(
                int(download_id), "Caminho de download ainda vazio")
            return

        archive_path = str(archive_path)
        _logger.debug(
            "Caminho de download obtido | id=%s | path=%s",
            int(download_id),
            archive_path,
        )
        if not self._wait_for_archive_path(archive_path, timeout_seconds=25.0):
            _logger.warning(
                f"Arquivo de download não ficou disponível a tempo: {archive_path}")
            self._schedule_download_retry(
                int(download_id), "Arquivo ainda não está pronto para instalação")
            return

        if self._get_bool("strictArchiveCheck", True) and not self._is_supported_archive(archive_path):
            _logger.info(
                f"Download ignorado (extensão não suportada): {archive_path}")
            self._schedule_download_retry(
                int(download_id), "Extensão temporária/inesperada no momento da leitura")
            return

        self._download_id_by_path[_norm_path(archive_path)] = int(download_id)
        self._download_retry_counts.pop(int(download_id), None)

        if not self._enqueue_install_path(archive_path):
            _logger.debug(
                "Download já presente em fila/inflight/dedupe | id=%s | path=%s",
                int(download_id),
                archive_path,
            )
            return

        _logger.info("Download enfileirado para instalação | id=%s | path=%s", int(
            download_id), archive_path)
        QTimer.singleShot(250, self._process_install_queue)

    def _is_duplicate_download_event(self, download_id: int) -> bool:
        now = time.time()
        self._prune_recent_map(self._recent_download_ids,
                               now, self._download_dedupe_ttl_seconds)

        if download_id in self._recent_download_ids:
            return True

        self._recent_download_ids[download_id] = now
        return False

    def _schedule_download_retry(self, download_id: int, reason: str) -> None:
        max_retries = self._get_int("autoInstallRetryCount", 8)
        attempt = int(self._download_retry_counts.get(int(download_id), 0)) + 1
        self._download_retry_counts[int(download_id)] = attempt

        if attempt > max_retries:
            _logger.error(
                f"Download {download_id} excedeu retentativas ({max_retries}). Último motivo: {reason}")
            self._download_retry_counts.pop(int(download_id), None)
            return

        delay_ms = self._download_retry_delay_ms_base * attempt
        _logger.info(
            f"Agendando retentativa #{attempt}/{max_retries} do download {download_id} em {delay_ms}ms: {reason}")
        QTimer.singleShot(
            int(delay_ms),
            lambda d=int(download_id): self._try_handle_download_complete(
                d, dedupe_event=False),
        )

    def _enqueue_install_path(self, archive_path: str) -> bool:
        normalized = _norm_path(archive_path)
        now = time.time()

        self._prune_recent_map(self._recent_install_paths,
                               now, self._install_dedupe_ttl_seconds)

        if normalized in self._pending_install_paths:
            return False
        if normalized in self._inflight_install_paths:
            return False

        last_seen = self._recent_install_paths.get(normalized)
        if last_seen is not None and (now - last_seen) < self._install_dedupe_ttl_seconds:
            return False

        self._pending_install_paths.add(normalized)
        self._install_queue.put(archive_path)
        return True

    def _mark_recent_install(self, archive_path: str) -> None:
        self._recent_install_paths[_norm_path(archive_path)] = time.time()

    def _wait_for_archive_path(self, archive_path: str, timeout_seconds: float) -> bool:
        deadline = time.time() + max(0.2, timeout_seconds)
        last_size: Optional[int] = None
        last_mtime: Optional[float] = None
        stable_since: Optional[float] = None

        while time.time() < deadline:
            if os.path.isfile(archive_path):
                try:
                    file_stat = os.stat(archive_path)
                    current_size = int(file_stat.st_size)
                    current_mtime = float(file_stat.st_mtime)
                except Exception:
                    current_size = None
                    current_mtime = None

                if current_size is not None and current_size > 0:
                    changed = (last_size != current_size) or (
                        last_mtime != current_mtime)

                    if changed:
                        stable_since = time.time()
                    else:
                        if stable_since is None:
                            stable_since = time.time()

                    is_stable = stable_since is not None and (
                        time.time() - stable_since) >= 1.2
                    last_size = current_size
                    last_mtime = current_mtime

                    # Para zip do Nexus, garante leitura válida do cabeçalho/central directory.
                    if is_stable and self._is_archive_content_ready(archive_path):
                        return True
            time.sleep(0.08)

        return self._is_archive_content_ready(archive_path)

    def _is_archive_content_ready(self, archive_path: str) -> bool:
        if not os.path.isfile(archive_path):
            return False

        try:
            if os.path.getsize(archive_path) <= 0:
                return False
        except Exception:
            return False

        # Zip é o formato mais comum do Nexus; validar abertura evita iniciar instalação em arquivo parcial.
        if archive_path.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(archive_path, "r") as zip_obj:
                    zip_obj.infolist()
                return True
            except (zipfile.BadZipFile, EOFError, OSError):
                return False

        return True

    def _is_supported_archive(self, archive_path: str) -> bool:
        valid_suffixes = (".7z", ".zip", ".rar", ".fomod", ".omod")
        return archive_path.lower().endswith(valid_suffixes)

    def _prune_recent_map(self, cache: Dict[Any, float], now: float, ttl_seconds: float) -> None:
        expired = [key for key, timestamp in cache.items() if (
            now - timestamp) >= ttl_seconds]
        for key in expired:
            cache.pop(key, None)

    def _record_install_event(self, mod: Any) -> None:
        now = time.time()
        self._prune_recent_map(
            self._installed_events_by_path, now, self._installed_event_ttl_seconds)
        self._prune_recent_map(
            self._installed_events_by_name, now, self._installed_event_ttl_seconds)

        try:
            install_file = str(mod.installationFile() or "").strip()
            if install_file:
                normalized = _norm_path(install_file)
                self._installed_events_by_path[normalized] = now

                name_only = os.path.basename(normalized)
                if name_only:
                    self._installed_events_by_name[name_only] = now
                _logger.info(
                    "Evento onModInstalled recebido | installFile=%s | baseName=%s",
                    normalized,
                    name_only,
                )
        except Exception:
            pass

    def _was_archive_installed_recently(self, archive_path: str, since_ts: float) -> bool:
        now = time.time()
        self._prune_recent_map(
            self._installed_events_by_path, now, self._installed_event_ttl_seconds)
        self._prune_recent_map(
            self._installed_events_by_name, now, self._installed_event_ttl_seconds)

        normalized = _norm_path(archive_path)
        by_path = self._installed_events_by_path.get(normalized)
        if by_path is not None and by_path >= since_ts:
            return True

        base_name = os.path.basename(normalized)
        by_name = self._installed_events_by_name.get(base_name)
        if by_name is not None and by_name >= since_ts:
            return True

        return False

    def _process_install_queue(self) -> None:
        if self._installing:
            return
        if not self._organizer:
            return

        self._installing = True
        try:
            while not self._install_queue.empty():
                queued_archive_path = self._install_queue.get()
                archive_path = str(queued_archive_path)
                normalized = _norm_path(archive_path)

                if normalized in self._inflight_install_paths:
                    continue

                self._pending_install_paths.discard(normalized)
                self._inflight_install_paths.add(normalized)
                installed_ok = False
                try:
                    _logger.info(
                        "Iniciando instalação automática | path=%s", archive_path)
                    installed_ok = self._install_archive(archive_path)
                    if not installed_ok:
                        download_id = self._download_id_by_path.get(normalized)
                        if download_id is not None:
                            _logger.warning(
                                "Instalação automática falhou; agendando nova retentativa | id=%s | path=%s",
                                int(download_id),
                                archive_path,
                            )
                            self._schedule_download_retry(
                                int(download_id),
                                "Falha ao instalar após tentativas locais",
                            )
                        else:
                            self._queue_manual_install(
                                archive_path,
                                "Falha no fluxo automático; necessário confirmar manualmente.",
                            )
                    elif self._get_bool("deleteDownloadAfterInstall", True):
                        self._cleanup_download_artifacts(archive_path)
                except Exception as exc:
                    _logger.error(f"Falha ao instalar '{archive_path}': {exc}")
                    self._queue_manual_install(
                        archive_path, f"Erro interno durante instalação: {exc}")
                finally:
                    if installed_ok:
                        self._mark_recent_install(archive_path)
                    self._inflight_install_paths.discard(normalized)
        except Exception as exc:
            _logger.error(f"Falha inesperada no processamento da fila: {exc}")
        finally:
            self._installing = False
            self._flush_manual_install_notice()

    def _install_archive(self, archive_path: str) -> bool:
        if not self._organizer:
            return False

        fast_install = self._get_bool("fastInstall", True)
        auto_replace = self._get_bool("autoReplace", True)

        first_try = self._run_install_attempt(
            archive_path,
            enable_fast_mode=fast_install,
            enable_auto_replace=auto_replace,
            timeout_seconds=6.0,
        )
        if first_try:
            return True

        second_try = self._run_install_attempt(
            archive_path,
            enable_fast_mode=True,
            enable_auto_replace=auto_replace,
            timeout_seconds=8.0,
        )
        return second_try

    def _run_install_attempt(
        self,
        archive_path: str,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
        timeout_seconds: float,
    ) -> bool:
        if not self._organizer:
            return False

        started_at = time.time()
        _logger.debug(
            "Tentativa de instalação iniciada | path=%s | fast=%s | autoReplace=%s | timeout=%.1fs",
            archive_path,
            bool(enable_fast_mode),
            bool(enable_auto_replace),
            float(timeout_seconds),
        )

        timer = self._start_install_assistant(
            timeout_seconds=timeout_seconds,
            enable_fast_mode=enable_fast_mode,
            enable_auto_replace=enable_auto_replace,
        )

        installed_mod = None
        try:
            sanitize_name = self._get_bool("sanitizeModName", True)
            title_case_name = self._get_bool("titleCaseModName", True)
            base_name = _sanitize_mod_name_from_archive(
                archive_path) if sanitize_name else os.path.splitext(os.path.basename(archive_path))[0]
            if title_case_name:
                base_name = _title_case_mod_name(base_name)
            _logger.info(
                f"Nome de instalação calculado: '{base_name}' (sanitize={sanitize_name}, titleCase={title_case_name})")

            try:
                installed_mod = self._organizer.installMod(
                    archive_path, base_name)
            except TypeError:
                try:
                    installed_mod = self._organizer.installMod(
                        archive_path, "")
                except TypeError:
                    installed_mod = self._organizer.installMod(archive_path)

            self._auto_confirm_install_dialog(
                timeout_seconds=1.4,
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            )
            event_wait_seconds = float(self._get_int(
                "autoInstallEventWaitSeconds", 4))
            if self._wait_for_install_event(archive_path, started_at, event_wait_seconds):
                _logger.info(
                    "Instalação confirmada por evento | path=%s | elapsed=%.2fs",
                    archive_path,
                    time.time() - started_at,
                )
                return True
        except Exception as exc:
            _logger.warning(
                f"Tentativa de instalação falhou para '{archive_path}': {exc}",
                exc_info=True,
            )
        finally:
            self._stop_install_assistant(timer)

        if self._is_successful_install_result(installed_mod):
            _logger.info(
                "Instalação confirmada por retorno installMod | path=%s | elapsed=%.2fs",
                archive_path,
                time.time() - started_at,
            )
            return True

        by_event = self._was_archive_installed_recently(
            archive_path, started_at - 0.5)
        _logger.debug(
            "Tentativa encerrada sem confirmação direta | path=%s | eventDetected=%s | elapsed=%.2fs",
            archive_path,
            bool(by_event),
            time.time() - started_at,
        )
        return by_event

    def _is_successful_install_result(self, install_result: Any) -> bool:
        if install_result is None:
            return False
        if isinstance(install_result, bool):
            return install_result
        if isinstance(install_result, int):
            return install_result != 0
        return True

    def _wait_for_install_event(self, archive_path: str, started_at: float, max_wait_seconds: float) -> bool:
        deadline = time.time() + max(0.6, max_wait_seconds)
        while time.time() < deadline:
            if self._was_archive_installed_recently(archive_path, started_at - 0.5):
                return True
            QApplication.processEvents()
            time.sleep(0.12)
        return self._was_archive_installed_recently(archive_path, started_at - 0.5)

    def _cleanup_download_artifacts(self, archive_path: str) -> None:
        normalized = _norm_path(archive_path)
        download_id = self._download_id_by_path.get(normalized)

        removed_via_manager = False
        if download_id is not None and self._download_manager is not None:
            removed_via_manager = self._remove_download_via_manager(
                download_id)

        removed_files = 0
        errors: List[str] = []
        for candidate in self._build_cleanup_candidates(archive_path):
            if not os.path.exists(candidate):
                continue
            ok, err = self._safe_delete_file(candidate)
            if ok:
                removed_files += 1
            elif err:
                errors.append(err)

        if removed_via_manager or removed_files > 0:
            _logger.info(
                f"Limpeza pós-instalação concluída para '{archive_path}' (manager={removed_via_manager}, files={removed_files})"
            )
        elif errors:
            _logger.warning(
                f"Falha parcial ao limpar download '{archive_path}': {' | '.join(errors[:3])}"
            )

        self._download_id_by_path.pop(normalized, None)

    def _build_cleanup_candidates(self, archive_path: str) -> List[str]:
        candidates = [archive_path]

        if self._get_bool("deleteDownloadSidecars", True):
            sidecars = [
                archive_path + ".meta",
                archive_path + ".nxm",
                archive_path + ".json",
                archive_path + ".download",
                archive_path + ".tmp",
            ]
            base_no_ext = os.path.splitext(archive_path)[0]
            sidecars.extend([
                base_no_ext + ".meta",
                base_no_ext + ".nxm",
                base_no_ext + ".json",
                base_no_ext + ".download",
                base_no_ext + ".tmp",
            ])
            candidates.extend(sidecars)

        dedup: List[str] = []
        seen: Set[str] = set()
        for item in candidates:
            key = _norm_path(item)
            if key in seen:
                continue
            seen.add(key)
            dedup.append(item)
        return dedup

    def _safe_delete_file(self, path_value: str) -> (bool, Optional[str]):
        attempts = 4
        for idx in range(attempts):
            try:
                if os.path.isfile(path_value):
                    os.remove(path_value)
                return True, None
            except Exception as exc:
                if idx < attempts - 1:
                    time.sleep(0.12)
                    continue
                return False, f"{os.path.basename(path_value)}: {exc}"
        return False, None

    def _remove_download_via_manager(self, download_id: int) -> bool:
        if self._download_manager is None:
            return False

        method_candidates = [
            "removeDownload",
            "deleteDownload",
            "removeFile",
            "remove",
        ]

        for method_name in method_candidates:
            method = getattr(self._download_manager, method_name, None)
            if method is None or not callable(method):
                continue

            attempts = [
                (download_id, True),
                (download_id, False),
                (download_id,),
            ]
            for args in attempts:
                try:
                    method(*args)
                    return True
                except TypeError:
                    continue
                except Exception:
                    continue

        return False

    def _start_install_assistant(
        self,
        timeout_seconds: float,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
    ) -> QTimer:
        timer = QTimer()
        timer.setInterval(90)
        started_at = time.time()

        def _on_tick() -> None:
            self._scan_install_dialogs(
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            )
            if (time.time() - started_at) >= max(0.8, timeout_seconds):
                self._stop_install_assistant(timer)

        timer.timeout.connect(_on_tick)
        self._active_dialog_timers.append(timer)
        timer.start()
        return timer

    def _stop_install_assistant(self, timer: Optional[QTimer]) -> None:
        if timer is None:
            return
        try:
            timer.stop()
            timer.deleteLater()
        except Exception:
            pass
        if timer in self._active_dialog_timers:
            self._active_dialog_timers.remove(timer)

    def _auto_confirm_install_dialog(
        self,
        timeout_seconds: float,
        enable_fast_mode: bool,
        enable_auto_replace: bool,
    ) -> bool:
        deadline = time.time() + max(0.08, timeout_seconds)
        action_taken = False

        while time.time() < deadline:
            if self._scan_install_dialogs(
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            ):
                action_taken = True
                QApplication.processEvents()
                return True
            time.sleep(0.05)

        return action_taken

    def _scan_install_dialogs(self, enable_fast_mode: bool, enable_auto_replace: bool) -> bool:
        QApplication.processEvents()
        try:
            top_levels = QApplication.topLevelWidgets()
        except Exception:
            return False

        acted = False
        for widget in top_levels:
            if self._handle_install_dialog(
                widget,
                enable_fast_mode=enable_fast_mode,
                enable_auto_replace=enable_auto_replace,
            ):
                acted = True
        return acted

    def _handle_install_dialog(self, widget: Any, enable_fast_mode: bool, enable_auto_replace: bool) -> bool:
        try:
            if widget is None or not widget.isVisible():
                return False
        except Exception:
            return False

        title = ""
        try:
            title = str(widget.windowTitle() or "").strip().lower()
        except Exception:
            pass

        conflict_markers = ["mod existe", "já está instalado",
                            "ja esta instalado", "already installed"]
        install_markers = [
            "instalação",
            "instalacao",
            "instalar",
            "quick install",
            "installation",
            "install",
            "query",
        ]

        is_conflict = any(marker in title for marker in conflict_markers)
        is_install = any(marker in title for marker in install_markers)

        if not is_conflict and not is_install:
            return False

        if is_conflict and enable_auto_replace:
            if self._click_by_markers(widget, ["repor", "replace", "substituir", "reinstalar", "overwrite"]):
                return True

        if is_install and enable_fast_mode:
            self._select_fast_install_mode(widget)

        if self._click_by_markers(widget, ["ok", "instalar", "install", "confirmar", "continuar", "aceitar"]):
            return True

        return False

    def _click_by_markers(self, widget: Any, markers: List[str]) -> bool:
        lowered_markers = [m.strip().lower() for m in markers if m.strip()]

        def _match(text_value: str) -> bool:
            normalized = str(text_value or "").strip().lower()
            return any(marker in normalized for marker in lowered_markers)

        try:
            for button in widget.findChildren(QPushButton):
                if button.isEnabled() and _match(button.text()):
                    button.click()
                    QApplication.processEvents()
                    return True
        except Exception:
            pass

        try:
            for box in widget.findChildren(QDialogButtonBox):
                try:
                    for button in box.buttons():
                        if button.isEnabled() and _match(button.text()):
                            button.click()
                            QApplication.processEvents()
                            return True
                except Exception:
                    continue
        except Exception:
            pass

        try:
            for button in widget.findChildren(QAbstractButton):
                if button.isEnabled() and _match(button.text()):
                    button.click()
                    QApplication.processEvents()
                    return True
        except Exception:
            pass

        return False

    def _select_fast_install_mode(self, widget: Any) -> None:
        fast_markers = ["rápida", "rapida", "quick", "express",
                        "automática", "automatica", "simple", "simples", "default"]
        manual_markers = ["manual"]

        try:
            for combo in widget.findChildren(QComboBox):
                try:
                    current_index = combo.currentIndex()
                    current_text = str(combo.currentText()
                                       or "").strip().lower()
                    target_index = -1

                    for index in range(combo.count()):
                        text = str(combo.itemText(index) or "").strip().lower()
                        if any(marker in text for marker in fast_markers):
                            target_index = index
                            break

                    if target_index < 0 and any(marker in current_text for marker in manual_markers):
                        for index in range(combo.count()):
                            if index == current_index:
                                continue
                            text = str(combo.itemText(index)
                                       or "").strip().lower()
                            if not any(marker in text for marker in manual_markers):
                                target_index = index
                                break

                    if target_index >= 0 and target_index != current_index:
                        combo.setCurrentIndex(target_index)
                        QApplication.processEvents()
                except Exception:
                    continue
        except Exception:
            pass

        try:
            for radio in widget.findChildren(QRadioButton):
                text = str(radio.text() or "").strip().lower()
                if radio.isEnabled() and any(marker in text for marker in fast_markers):
                    radio.setChecked(True)
                    QApplication.processEvents()
                    break
        except Exception:
            pass

    def _queue_manual_install(self, archive_path: str, reason: str) -> None:
        self._manual_install_items.append(
            {
                "archive": os.path.basename(archive_path),
                "reason": reason,
            }
        )

    def _flush_manual_install_notice(self) -> None:
        if not self._manual_install_items:
            return

        lines: List[str] = []
        for item in self._manual_install_items[:8]:
            lines.append(f"- {item['archive']}: {item['reason']}")

        extra = len(self._manual_install_items) - len(lines)
        if extra > 0:
            lines.append(f"- ... e mais {extra} item(ns).")

        message = (
            "Alguns downloads exigiram confirmação manual para finalizar corretamente.\n\n"
            + "\n".join(lines)
        )
        self._manual_install_items.clear()

        parent = QApplication.activeWindow()
        if parent is not None:
            try:
                QMessageBox.information(
                    parent, "MO2Tools - Atenção na Instalação", message)
                return
            except Exception:
                pass

        _logger.warning(message)
