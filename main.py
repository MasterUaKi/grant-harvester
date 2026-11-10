# File: main.py
# Version: 1.0.0 | Release Date: 2026-11-10
"""
EN: Main daemon entrypoint for the autonomous academic grant monitoring framework.
DE: Haupt-Daemon-Einstiegspunkt für das autonome Framework zur Überwachung akademischer Förderungen.
"""

import asyncio
import logging
import signal
import sys
from config import settings
from harvester import MultiPortalGrantHarvester

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GrantHarvesterDaemon")


class GrantHarvesterDaemon:
    """
    EN: Periodic daemon runner executing autonomous harvest and lifecycle maintenance.
    DE: Periodischer Daemon zur Durchführung autonomer Erfassungs- und Pflegezyklen.
    """

    def __init__(self):
        self._running = False
        self._harvester: MultiPortalGrantHarvester | None = None

    def stop(self):
        """
        EN: Gracefully signals the daemon loop to stop.
        DE: Beendet die Ausführungsschleife des Daemons ordnungsgemäß.
        """
        logger.info("Stopping daemon service / Stoppe Daemon-Dienst...")
        self._running = False

    async def run(self):
        """
        EN: Executes continuous scheduled monitoring cycles.
        DE: Führt fortlaufende, zeitgesteuerte Überwachungszyklen aus.
        """
        self._running = True
        logger.info(
            "Starting Autonomous Grant Monitoring Daemon / Starte autonomen Förderungs-Überwachungsdienst "
            f"(Interval / Intervall: {settings.INTERVAL_MINUTES} min)..."
        )

        while self._running:
            try:
                self._harvester = MultiPortalGrantHarvester()
                await self._harvester.run_full_harvest_cycle()
            except Exception as err:
                logger.error(
                    f"Unexpected error during harvest cycle / Unerwarteter Fehler im Erfassungszyklus: {err}",
                    exc_info=True
                )
            finally:
                if self._harvester and hasattr(self._harvester, "browser_engine"):
                    try:
                        await self._harvester.browser_engine.close()
                    except Exception:
                        pass
                self._harvester = None

            if not self._running:
                break

            logger.info(
                f"Cycle completed. Sleeping for {settings.INTERVAL_MINUTES} minutes / "
                f"Zyklus abgeschlossen. Pause für {settings.INTERVAL_MINUTES} Minuten..."
            )

            # EN: Sleep in small increments to respond quickly to shutdown signals
            # DE: In kurzen Abständen pausieren, um zügig auf Beendigungssignale zu reagieren
            for _ in range(settings.INTERVAL_MINUTES * 60):
                if not self._running:
                    break
                await asyncio.sleep(1)

        logger.info("Daemon service stopped cleanly / Daemon-Dienst sauber beendet.")


async def main():
    daemon = GrantHarvesterDaemon()

    def handle_signal():
        daemon.stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except NotImplementedError:
            # EN: Windows event loop signal fallback / DE: Signal-Fallback für Windows Event Loop
            pass

    await daemon.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated by user / Prozess durch Benutzer beendet.")