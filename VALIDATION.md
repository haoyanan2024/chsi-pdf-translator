# Validation for 1.2.0

Validated on the current Windows x64 host (Python 3.12.14) and the designated
Ubuntu 22.04.5 x86_64 server (Python 3.10.12). No claim is made of a complete
Windows version or historical CHSI document-layout compatibility matrix.

## Adaptive fields and layout

The main table now defaults to all recognized fields present in the Chinese
source, in their source order, including rows whose values are blank. College,
department, class and student number use the main table. Each field can be shown
or hidden independently; there is no appendix option or appendix output.

The upstream ornamental template and fonts remain bundled. At export, the old
table labels are removed as text operations and selected labels/values are laid
out together. No white cover rectangles are used. Normal rows use 8.6 pt Roboto
and 28 pt spacing. Long values wrap; row height, spacing and font size adapt to
available space while reserving the photo and verification panel. The minimum
body font is 7.8 pt. Content exceeding the single-page limit produces a clear
error rather than overlapping or dropping content.

## Regression results

All 31 pytest cases passed on both Windows and Linux. Coverage includes:

- Default source field order and blank college preservation.
- Optional absent fields remaining unselected.
- Hiding labels and values together, with subsequent rows moving upward.
- Long values avoiding the photo when early fields are hidden.
- All 17 supported main-table fields plus wrapped text fitting on one page.
- Non-overlap between adjacent row text and the lower verification area.
- Independent date, verification-code and source-note visibility.
- Hidden pending fields not blocking export or entering optional online translation.
- Restoring source visibility without changing translation values.
- Draft schema 2 preserving visibility and schema 1 migrating with source defaults.
- Background graphics unchanged outside designated text/image regions.
- Original portrait and QR pixel equality after export.
- Offline extraction, wrapped Chinese, blank fields and compound surname handling.
- Unknown vocabulary, date validation, literal markup and remaining Chinese checks.
- Encrypted, corrupt, unrelated and multiple-report PDFs.
- Source overwrite protection, changed source notes and mocked network quota errors.

The frozen GUI self-test also exercises automatic English preview, editable
translations, checkbox changes, preview regeneration and the restore button.

## User report and visual review

The user-supplied report was processed locally. The default PDF contains 15 main
rows: the original 13 template fields plus the blank college and populated
department rows. A second variant hides college/department and closes both gaps.
A stress variant adds class/student number and uses a two-line major translation.
All three were rendered with Poppler and visually reviewed: border/background,
alignment, readable text, portrait and QR placement are intact.

The interface was rendered and inspected with both default and hidden selections.
Automatic preview, scrolling, checkbox state, disabled-field color, displayed
field count and restoring source selection behaved as expected.

No expiry date was present in the source, so none is invented. The original
one-to-six-month validity note is retained in translation. Original photo and QR
pixels were compared against the installed program's exported PDF and matched.

## Server package

The public source archive was uploaded into the designated testing directory and
installed in its existing isolated Python environment. No user report, private
photo, QR or credential was included in the upload. All 31 tests and
`--self-test --headless` passed.

From outside the source directory, the installed package converted the synthetic
Chinese sample, saved a schema-2 draft, restored that draft, and exported another
PDF using `--hide college --hide department`. This verifies that template/fonts
are included in the installed Python package and that the server requires no Qt
or graphical desktop. Logs and synthetic outputs remain in the server project.

## Windows installer

The 1.2.0 installer was installed into a temporary directory containing Chinese
characters. With PATH restricted to Windows system directories, the installed
EXE passed self-test with the native `windows` Qt plugin, including automatic
preview and visibility/reset controls. It converted the real user PDF in both
default and hidden-field modes without an external Python runtime.

Both installed-program PDFs rendered pixel-identically to the corresponding
source-program PDFs at 144 dpi. The temporary installation was then uninstalled:
its executable and uninstall registration were removed, and PDFs were retained.

## Delivery scope

Source packaging uses an explicit allowlist. The only public PDF is the sanitized
upstream template; only the two named Roboto font files are included as fonts.
Private reports, drafts, images, credentials and test output are excluded.
Release hashes are supplied in `SHA256SUMS.txt`.

The optional MyMemory service was tested with mocked responses. The GitHub
workflow is supplied but was not run on GitHub in this local delivery. Windows
executables are unsigned. See README.md for usage and rebuilding instructions.
