/**
 * Cover page with Luckin Coffee branding.
 */

const {
  Paragraph,
  TextRun,
  AlignmentType,
  PageBreak,
  Tab,
  BorderStyle,
} = require('docx');

const { COLORS, FONTS, FONT_SIZES } = require('../styles');
const { spacer } = require('../utils');

function buildCoverPage(metadata) {
  return {
    properties: {
      page: {
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    children: [
      // Top spacer
      spacer(1200),
      spacer(1200),
      spacer(1200),

      // Blue accent line
      new Paragraph({
        spacing: { after: 400 },
        border: {
          bottom: {
            style: BorderStyle.SINGLE,
            size: 12,
            color: COLORS.NAVY,
            space: 10,
          },
        },
        children: [],
      }),

      // Company name
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: '瑞幸咖啡北美',
            font: FONTS.HEADING,
            size: 36, // 18pt
            color: COLORS.BLUE_ACCENT,
          }),
        ],
      }),

      // Main title
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [
          new TextRun({
            text: 'QA门店巡检月度分析报告',
            font: FONTS.HEADING,
            size: 52, // 26pt
            bold: true,
            color: COLORS.NAVY,
          }),
        ],
      }),

      // English subtitle
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: 'Monthly QA Store Audit Analysis Report',
            font: FONTS.BODY,
            size: FONT_SIZES.H2,
            color: COLORS.BLUE_ACCENT,
            italics: true,
          }),
        ],
      }),

      // Month
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [
          new TextRun({
            text: metadata.analysis_month_cn,
            font: FONTS.HEADING,
            size: 40, // 20pt
            bold: true,
            color: COLORS.NAVY,
          }),
        ],
      }),

      // Bottom accent line
      new Paragraph({
        spacing: { before: 400, after: 400 },
        border: {
          top: {
            style: BorderStyle.SINGLE,
            size: 12,
            color: COLORS.NAVY,
            space: 10,
          },
        },
        children: [],
      }),

      spacer(400),

      // Department
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [
          new TextRun({
            text: '质量保障部 / 基础设施部',
            font: FONTS.HEADING,
            size: FONT_SIZES.H3,
            color: COLORS.TEXT_DARK,
          }),
        ],
      }),

      // Author
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [
          new TextRun({
            text: `编制：${metadata.author}`,
            font: FONTS.BODY,
            size: FONT_SIZES.BODY,
            color: COLORS.TEXT_DARK,
          }),
        ],
      }),

      // Date
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [
          new TextRun({
            text: `日期：${metadata.analysis_date}`,
            font: FONTS.BODY,
            size: FONT_SIZES.BODY,
            color: COLORS.TEXT_DARK,
          }),
        ],
      }),

      // Page break after cover
      new Paragraph({
        children: [new PageBreak()],
      }),
    ],
  };
}

module.exports = { buildCoverPage };
