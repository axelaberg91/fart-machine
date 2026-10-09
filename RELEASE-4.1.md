# Version 4.1

- Published the approved original-photo theme, using cropped and resized user-provided photos. No AI-generated or retouched faces.
- Simplified the area above the volume controls to just the app title: Hugo och Hermans pruttmaskin.
- Removed the new-recordings banner and the repeated recorded-audio labels on buttons.
- Preserved the nine existing recorded MP3 files, sound names, volume, orchestra mode and Stop all.
- Kept a visible Version 4.1 footer. The offline cache includes all nine photos and all nine recordings.

Validation: JavaScript syntax checks passed. In-memory Chromium layout/preview tests passed at widths 320, 390, 834 and 1280 pixels, including all nine photos, title-only header, no horizontal overflow and preview click/Stop behavior. This release was not auditioned on a physical iPhone/iPad, and the deployed service-worker lifecycle was not tested end to end in Safari.
