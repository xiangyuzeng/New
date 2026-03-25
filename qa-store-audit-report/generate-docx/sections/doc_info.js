/**
 * Document information table.
 */

const { Paragraph, TextRun, PageBreak } = require('docx');
const { buildTable, heading1, spacer } = require('../utils');

function buildDocInfo(metadata) {
  const infoRows = [
    ['报告编号', metadata.report_id],
    ['报告周期', metadata.analysis_month_cn],
    ['数据范围', `${metadata.date_range.start} 至 ${metadata.date_range.end}`],
    ['门店数量', `${metadata.total_stores} 家`],
    ['巡检次数', `${metadata.total_inspections} 次`],
    ['编制人', metadata.author],
    ['编制日期', metadata.analysis_date],
    ['部门', '质量保障部 / 基础设施部'],
    ['密级', '内部文件'],
    ['状态', '终稿'],
  ];

  return {
    properties: {
      page: {
        margin: { top: 1440, right: 1080, bottom: 1440, left: 1080 },
      },
    },
    children: [
      heading1('文档信息'),
      spacer(100),
      buildTable(
        ['项目', '内容'],
        infoRows,
        { colWidths: [30, 70] }
      ),
      spacer(200),
      new Paragraph({
        children: [new PageBreak()],
      }),
    ],
  };
}

module.exports = { buildDocInfo };
