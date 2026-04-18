from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSSynthesizer(Protocol):
    """Common interface for all TTS backends.

    Implementors must provide:
    - load(): initialise model weights into memory
    - synthesize(): convert sentences to an MP3 file
    """

    def load(self) -> None:
        """Load model weights. Called once at container startup."""
        ...

    def synthesize(
        self,
        sentences: list[tuple[str, bool]],
        output_path: Path,
    ) -> Path:
        """Synthesize sentences to an MP3 file.

        Args:
            sentences: list of (text, is_paragraph_end) tuples.
                       is_paragraph_end=True triggers a longer inter-sentence pause.
            output_path: destination path for the MP3 file.

        Returns:
            output_path on success.
        """
        ...
