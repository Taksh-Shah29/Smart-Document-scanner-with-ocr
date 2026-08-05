"""GUI application module for Smart Document Scanner."""

import customtkinter as ctk


class SmartDocumentScannerApp(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Smart Document Scanner")
        self.geometry("1024x720")
        self._configure_ui()

    def _configure_ui(self) -> None:
        """Set up the main UI layout."""
        self.label = ctk.CTkLabel(self, text="Smart Document Scanner", font=("Arial", 24))
        self.label.pack(pady=20)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(padx=20, pady=20, fill="x")

        self.upload_button = ctk.CTkButton(self.button_frame, text="Upload Image", command=self._not_implemented)
        self.upload_button.grid(row=0, column=0, padx=10, pady=10)

        self.scan_button = ctk.CTkButton(self.button_frame, text="Scan Document", command=self._not_implemented)
        self.scan_button.grid(row=0, column=1, padx=10, pady=10)

        self.extract_button = ctk.CTkButton(self.button_frame, text="Extract Text", command=self._not_implemented)
        self.extract_button.grid(row=0, column=2, padx=10, pady=10)

        self.save_pdf_button = ctk.CTkButton(self.button_frame, text="Save PDF", command=self._not_implemented)
        self.save_pdf_button.grid(row=0, column=3, padx=10, pady=10)

        self.copy_text_button = ctk.CTkButton(self.button_frame, text="Copy Text", command=self._not_implemented)
        self.copy_text_button.grid(row=0, column=4, padx=10, pady=10)

        self.exit_button = ctk.CTkButton(self.button_frame, text="Exit", command=self.destroy)
        self.exit_button.grid(row=0, column=5, padx=10, pady=10)

    def _not_implemented(self) -> None:
        """Placeholder for future implementations."""
        pass

    def run(self) -> None:
        """Start the application main loop."""
        self.mainloop()
