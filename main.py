"""Smart Document Scanner entry point."""

from gui.app import SmartDocumentScannerApp


def main() -> None:
    app = SmartDocumentScannerApp()
    app.run()


if __name__ == "__main__":
    main()
