/**
 * Section 1: 门店整体表现 (Store Overall Performance).
 */

const { Paragraph, TextRun, AlignmentType } = require('docx');
const { COLORS, FONTS, FONT_SIZES, scoreColor } = require('../styles');
const {
  buildTable,
  heading1,
  heading2,
  bodyText,
  bulletPoint,
  spacer,
  multiRunParagraph,
} = require('../utils');

function buildSection1(layer1, metadata) {
  const children = [];

  children.push(heading1('一、门店整体表现'));

  // Overview stats
  children.push(heading2('1.1 本月概览'));

  const avg = layer1.monthly_average;
  const avgColor = scoreColor(avg);

  children.push(
    multiRunParagraph([
      new TextRun({
        text: `本月巡检覆盖 `,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: COLORS.TEXT_DARK,
      }),
      new TextRun({
        text: `${layer1.total_stores_scored} 家门店`,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: COLORS.NAVY,
        bold: true,
      }),
      new TextRun({
        text: `，平均得分 `,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: COLORS.TEXT_DARK,
      }),
      new TextRun({
        text: `${avg} 分`,
        font: FONTS.BODY,
        size: FONT_SIZES.BODY,
        color: avgColor,
        bold: true,
      }),
      ...(layer1.prior_month_average != null
        ? [
            new TextRun({
              text: `（上月 ${layer1.prior_month_average} 分，`,
              font: FONTS.BODY,
              size: FONT_SIZES.BODY,
              color: COLORS.TEXT_DARK,
            }),
            new TextRun({
              text: layer1.average_trend >= 0
                ? `↑ ${layer1.average_trend}`
                : `↓ ${Math.abs(layer1.average_trend)}`,
              font: FONTS.BODY,
              size: FONT_SIZES.BODY,
              color: layer1.average_trend >= 0 ? COLORS.GREEN : COLORS.RED,
              bold: true,
            }),
            new TextRun({
              text: '）',
              font: FONTS.BODY,
              size: FONT_SIZES.BODY,
              color: COLORS.TEXT_DARK,
            }),
          ]
        : []),
    ])
  );

  // Highest / Lowest
  if (layer1.highest_store && layer1.highest_store.name) {
    children.push(bulletPoint(
      `最高分门店：${layer1.highest_store.name}（${layer1.highest_store.score} 分）`,
      { color: COLORS.GREEN }
    ));
  }
  if (layer1.lowest_store && layer1.lowest_store.name) {
    children.push(bulletPoint(
      `最低分门店：${layer1.lowest_store.name}（${layer1.lowest_store.score} 分）`,
      { color: COLORS.RED }
    ));
  }

  // Most improved / declined
  if (layer1.most_improved) {
    children.push(bulletPoint(
      `进步最大：${layer1.most_improved.name}（+${layer1.most_improved.change} 分，${layer1.most_improved.prior_score} → ${layer1.most_improved.current_score}）`,
      { color: COLORS.GREEN }
    ));
  }
  if (layer1.most_declined) {
    children.push(bulletPoint(
      `退步最大：${layer1.most_declined.name}（${layer1.most_declined.change} 分，${layer1.most_declined.prior_score} → ${layer1.most_declined.current_score}）`,
      { color: COLORS.RED }
    ));
  }

  children.push(spacer(200));

  // Store scores table
  children.push(heading2('1.2 各门店得分明细'));

  const headers = ['排名', '门店名称', '门店编号', '城市', '得分', '门店类型'];
  const hasPrior = layer1.store_scores.some(s => s.prior_score != null);
  if (hasPrior) {
    headers.push('上月得分', '变化');
  }

  const rows = layer1.store_scores.map((store, idx) => {
    const row = [
      String(idx + 1),
      store.store_name,
      store.store_serial,
      store.city || '',
      String(store.latest_score),
      store.store_level || '',
    ];
    if (hasPrior) {
      row.push(
        store.prior_score != null ? String(store.prior_score) : '-',
        store.change != null
          ? (store.change >= 0 ? `+${store.change}` : String(store.change))
          : '-'
      );
    }
    return row;
  });

  const colWidths = hasPrior
    ? [7, 18, 13, 13, 10, 12, 12, 10]
    : [8, 22, 15, 17, 13, 15];

  children.push(
    buildTable(headers, rows, {
      colWidths,
      cellFormatter: (value, rowIdx, colIdx) => {
        // Color the score column
        const scoreColIdx = 4;
        if (colIdx === scoreColIdx) {
          const score = parseFloat(value);
          if (!isNaN(score)) {
            return { color: scoreColor(score), bold: true };
          }
        }
        // Color the change column (last col if hasPrior)
        if (hasPrior && colIdx === headers.length - 1 && value !== '-') {
          const change = parseFloat(value);
          if (!isNaN(change)) {
            return {
              color: change >= 0 ? COLORS.GREEN : COLORS.RED,
              bold: true,
            };
          }
        }
        return {};
      },
    })
  );

  // Anomalous scores note
  if (layer1.anomalous_scores && layer1.anomalous_scores.length > 0) {
    children.push(spacer(200));
    children.push(heading2('1.3 数据质量说明'));
    children.push(bodyText(
      `检测到 ${layer1.anomalous_scores.length} 条异常负分数据（可能来自不同评分基准的巡检类别），已从统计计算中排除：`
    ));

    const anomRows = layer1.anomalous_scores.map(a => [
      a.store_name,
      String(a.score),
      a.check_date,
      a.check_category || '',
    ]);
    children.push(
      buildTable(
        ['门店', '异常分数', '检查日期', '检查类别'],
        anomRows,
        { colWidths: [25, 15, 20, 40] }
      )
    );
  }

  children.push(spacer(200));

  return {
    properties: {
      page: {
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 },
      },
    },
    children,
  };
}

module.exports = { buildSection1 };
