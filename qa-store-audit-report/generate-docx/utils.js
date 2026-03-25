/**
 * Shared DOCX generation utilities.
 * Table builder, text helpers, status badges.
 */

const {
  Table,
  TableRow,
  TableCell,
  Paragraph,
  TextRun,
  WidthType,
  AlignmentType,
  VerticalAlign,
  BorderStyle,
} = require('docx');

const {
  COLORS,
  FONTS,
  FONT_SIZES,
  tableBorders,
  headerShading,
  altRowShading,
  scoreColor,
  severityColor,
} = require('./styles');

/**
 * Create a styled table with navy header and alternating rows.
 *
 * @param {string[]} headers - Column header texts
 * @param {Array<string[]>} rows - Array of row data (strings)
 * @param {Object} [options] - Optional settings
 * @param {number[]} [options.colWidths] - Column widths in percentage (should sum to 100)
 * @param {Function} [options.cellFormatter] - (value, rowIdx, colIdx) => object with optional { color, shading, bold }
 * @returns {Table}
 */
function buildTable(headers, rows, options = {}) {
  const { colWidths, cellFormatter } = options;

  // Header row
  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map((text, i) =>
      new TableCell({
        shading: headerShading(),
        verticalAlign: VerticalAlign.CENTER,
        width: colWidths
          ? { size: colWidths[i], type: WidthType.PERCENTAGE }
          : undefined,
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                text: text,
                bold: true,
                color: COLORS.WHITE,
                font: FONTS.HEADING,
                size: FONT_SIZES.SMALL,
              }),
            ],
          }),
        ],
      })
    ),
  });

  // Data rows
  const dataRows = rows.map((rowData, rowIdx) =>
    new TableRow({
      children: rowData.map((cellText, colIdx) => {
        const fmt = cellFormatter
          ? cellFormatter(cellText, rowIdx, colIdx)
          : {};

        return new TableCell({
          shading: fmt.shading || altRowShading(rowIdx),
          verticalAlign: VerticalAlign.CENTER,
          width: colWidths
            ? { size: colWidths[colIdx], type: WidthType.PERCENTAGE }
            : undefined,
          children: [
            new Paragraph({
              alignment: fmt.alignment || AlignmentType.CENTER,
              children: [
                new TextRun({
                  text: String(cellText),
                  bold: fmt.bold || false,
                  color: fmt.color || COLORS.TEXT_DARK,
                  font: FONTS.BODY,
                  size: FONT_SIZES.SMALL,
                }),
              ],
            }),
          ],
        });
      }),
    })
  );

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    borders: tableBorders(),
    rows: [headerRow, ...dataRows],
  });
}

/**
 * Create a heading paragraph (H1 style).
 */
function heading1(text) {
  return new Paragraph({
    spacing: { before: 360, after: 200 },
    children: [
      new TextRun({
        text,
        bold: true,
        font: FONTS.HEADING,
        size: FONT_SIZES.H1,
        color: COLORS.NAVY,
      }),
    ],
  });
}

/**
 * Create a sub-heading paragraph (H2 style).
 */
function heading2(text) {
  return new Paragraph({
    spacing: { before: 240, after: 120 },
    children: [
      new TextRun({
        text,
        bold: true,
        font: FONTS.HEADING,
        size: FONT_SIZES.H2,
        color: COLORS.BLUE_ACCENT,
      }),
    ],
  });
}

/**
 * Create a heading3 paragraph.
 */
function heading3(text) {
  return new Paragraph({
    spacing: { before: 200, after: 100 },
    children: [
      new TextRun({
        text,
        bold: true,
        font: FONTS.HEADING,
        size: FONT_SIZES.H3,
        color: COLORS.NAVY,
      }),
    ],
  });
}

/**
 * Create a body text paragraph.
 */
function bodyText(text, options = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    alignment: options.alignment || AlignmentType.LEFT,
    children: [
      new TextRun({
        text,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: options.color || COLORS.TEXT_DARK,
        bold: options.bold || false,
        italics: options.italics || false,
      }),
    ],
  });
}

/**
 * Create a colored status badge text run.
 */
function statusBadge(level, text) {
  const colorMap = {
    critical: COLORS.RED,
    warning: COLORS.WARNING,
    healthy: COLORS.GREEN,
    info: COLORS.BLUE_ACCENT,
    S: COLORS.RED,
    M: COLORS.WARNING,
    G: COLORS.BLUE_ACCENT,
    L: COLORS.TEXT_DARK,
  };

  return new TextRun({
    text: ` ${text} `,
    bold: true,
    color: colorMap[level] || COLORS.TEXT_DARK,
    font: FONTS.BODY,
    size: FONT_SIZES.BODY,
  });
}

/**
 * Format a score with conditional coloring.
 */
function formatScoreRun(score) {
  return new TextRun({
    text: String(score),
    bold: true,
    color: scoreColor(score),
    font: FONTS.BODY,
    size: FONT_SIZES.BODY,
  });
}

/**
 * Create a bullet point paragraph.
 */
function bulletPoint(text, options = {}) {
  return new Paragraph({
    spacing: { after: 60 },
    indent: { left: 360 },
    children: [
      new TextRun({
        text: `• ${text}`,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: options.color || COLORS.TEXT_DARK,
        bold: options.bold || false,
      }),
    ],
  });
}

/**
 * Create an empty paragraph as spacer.
 */
function spacer(heightTwips = 200) {
  return new Paragraph({
    spacing: { after: heightTwips },
    children: [],
  });
}

/**
 * Create a multi-run paragraph.
 */
function multiRunParagraph(runs, options = {}) {
  return new Paragraph({
    spacing: { after: options.spacingAfter || 120 },
    alignment: options.alignment || AlignmentType.LEFT,
    children: runs,
  });
}

module.exports = {
  buildTable,
  heading1,
  heading2,
  heading3,
  bodyText,
  statusBadge,
  formatScoreRun,
  bulletPoint,
  spacer,
  multiRunParagraph,
};
