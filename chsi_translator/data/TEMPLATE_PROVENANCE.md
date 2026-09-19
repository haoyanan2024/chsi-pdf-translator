# Template and font provenance

Source: https://github.com/muxiymmm/Online-Verification-Report-Translator20260714

Pinned commit: `7cc3e94b9e28197d8dd85dccf93a4f105b4d4a5e` (Apache-2.0).

- Template: `data/online_verification_report_template20260809.pdf`
  (Git blob `f37b674d58384cb4228a13efb3ab6d0299c01399`).
- Roboto Regular: `font/Roboto-Regular.ttf`
  (Git blob `7d9a6c4c32d7e920b549caf531e390733496b6e0`).
- Roboto Medium: `font/Roboto-Medium.ttf`
  (Git blob `87983419893a8952c3f286dc56d37fb94e320da0`).

The two font files are unmodified. Embedded font copyright: Google 2011.
Roboto's Apache-2.0 license: https://github.com/googlefonts/roboto-2/blob/main/LICENSE
Verbatim notices are included under `licenses/UpstreamTemplate` and `licenses/Roboto`.

## Changes to the template

`scripts/prepare_template.py` removes 15 hidden example text drawing operations
and the example portrait and QR image resources. The upstream template covers
these with background patches but still exposes them through text/image
extraction. The patches, ornamental border, watermark, labels, logo and page
geometry remain unchanged. Rendered output was pixel-identical at 144 dpi before
and after this cleanup. No example personal files are bundled.

Since 1.2.0, export removes the original main-table label drawing operations,
source-note operations and verification-code label, retaining their underlying
background. Selected labels and values are then drawn together in source order.
College, department, class and student number use the same main table. No appendix
is generated. The default selection matches source fields, including empty rows;
users can independently show/hide fields and save these choices in draft schema 2.

The default main-table typography remains 8.6 pt Roboto Regular and 28 pt row
spacing, starting at the upstream table origin. Wrapped content expands its row;
denser selections reduce row spacing and, if needed, font size down to 7.8 pt.
The algorithm measures all rows before drawing, reserving the portrait and lower
verification panel. Excessive content raises an error rather than overlapping.
The verification code remains 10 pt Roboto Medium; portrait and QR placement use
the upstream dimensions. The template's explanatory note, logo, border and
background remain unchanged. Source-note text and dates use the imported report;
no expiry date or validity duration is inferred from the example template.
