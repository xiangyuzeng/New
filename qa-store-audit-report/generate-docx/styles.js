/**
 * Luckin Coffee QA Report — DOCX Theme Styles.
 * Colors, fonts, table borders, shading helpers.
 */

const { BorderStyle, ShadingType, AlignmentType } = require('docx');

// Colors (hex without # for docx library)
const COLORS = {
  NAVY: '1F4E79',
  BLUE_ACCENT: '2E75B6',
  LIGHT_BLUE_BG: 'D6E4F0',
  ALT_ROW: 'F2F2F2',
  BORDER_GRAY: 'BFBFBF',
  TEXT_DARK: '2C3E50',
  WHITE: 'FFFFFF',
  BLACK: '000000',
  GREEN: '27AE60',
  RED: 'C0392B',
  WARNING: 'E67E22',
  CRITICAL_BG: 'FCE4EC',
  WARNING_BG: 'FDEBD0',
  HEALTHY_BG: 'D5F5E3',
  INFO_BG: 'D6E4F0',
};

// Font families
const FONTS = {
  HEADING: 'Microsoft YaHei',     // 微软雅黑
  HEADING_FALLBACK: 'Arial',
  BODY: 'Arial',
  BODY_CN: 'SimSun',             // 宋体
  MONO: 'Consolas',
};

// Font sizes in half-points (docx uses half-points)
const FONT_SIZES = {
  TITLE: 32,      // 16pt
  H1: 32,         // 16pt
  H2: 26,         // 13pt
  H3: 24,         // 12pt
  BODY: 22,       // 11pt
  SMALL: 20,      // 10pt
  CAPTION: 18,    // 9pt
};

/**
 * Standard table borders.
 */
function tableBorders() {
  const border = {
    style: BorderStyle.SINGLE,
    size: 1,
    color: COLORS.BORDER_GRAY,
  };
  return {
    top: border,
    bottom: border,
    left: border,
    right: border,
    insideHorizontal: border,
    insideVertical: border,
  };
}

/**
 * Header cell shading (navy background).
 */
function headerShading() {
  return {
    type: ShadingType.CLEAR,
    fill: COLORS.NAVY,
    color: COLORS.WHITE,
  };
}

/**
 * Alternating row shading.
 */
function altRowShading(rowIndex) {
  if (rowIndex % 2 === 1) {
    return {
      type: ShadingType.CLEAR,
      fill: COLORS.ALT_ROW,
    };
  }
  return undefined;
}

/**
 * Status-based shading (for highlighting cells).
 */
function statusShading(level) {
  const map = {
    critical: { type: ShadingType.CLEAR, fill: COLORS.CRITICAL_BG },
    warning: { type: ShadingType.CLEAR, fill: COLORS.WARNING_BG },
    healthy: { type: ShadingType.CLEAR, fill: COLORS.HEALTHY_BG },
    info: { type: ShadingType.CLEAR, fill: COLORS.INFO_BG },
  };
  return map[level] || undefined;
}

/**
 * Score-based color.
 */
function scoreColor(score) {
  if (score >= 90) return COLORS.GREEN;
  if (score >= 80) return COLORS.TEXT_DARK;
  return COLORS.RED;
}

/**
 * Severity-based color.
 */
function severityColor(code) {
  const map = {
    S: COLORS.RED,
    M: COLORS.WARNING,
    G: COLORS.BLUE_ACCENT,
    L: COLORS.TEXT_DARK,
    O: COLORS.BORDER_GRAY,
  };
  return map[code] || COLORS.TEXT_DARK;
}

/**
 * Document-level style definitions for the docx Document constructor.
 */
function documentStyles() {
  return {
    default: {
      document: {
        run: {
          font: FONTS.BODY,
          size: FONT_SIZES.BODY,
          color: COLORS.TEXT_DARK,
        },
        paragraph: {
          spacing: { after: 120 },
        },
      },
    },
    paragraphStyles: [
      {
        id: 'Title',
        name: 'Title',
        basedOn: 'Normal',
        next: 'Normal',
        run: {
          font: FONTS.HEADING,
          size: 48, // 24pt
          bold: true,
          color: COLORS.NAVY,
        },
        paragraph: {
          alignment: AlignmentType.CENTER,
          spacing: { after: 200 },
        },
      },
      {
        id: 'Heading1',
        name: 'Heading 1',
        basedOn: 'Normal',
        next: 'Normal',
        run: {
          font: FONTS.HEADING,
          size: FONT_SIZES.H1,
          bold: true,
          color: COLORS.NAVY,
        },
        paragraph: {
          spacing: { before: 360, after: 200 },
        },
      },
      {
        id: 'Heading2',
        name: 'Heading 2',
        basedOn: 'Normal',
        next: 'Normal',
        run: {
          font: FONTS.HEADING,
          size: FONT_SIZES.H2,
          bold: true,
          color: COLORS.BLUE_ACCENT,
        },
        paragraph: {
          spacing: { before: 240, after: 120 },
        },
      },
    ],
  };
}

module.exports = {
  COLORS,
  FONTS,
  FONT_SIZES,
  tableBorders,
  headerShading,
  altRowShading,
  statusShading,
  scoreColor,
  severityColor,
  documentStyles,
};
