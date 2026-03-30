const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, HeadingLevel, BorderStyle, ShadingType,
  PageBreak, Header, Footer, ImageRun, TableOfContents,
  convertInchesToTwip, PageNumber, NumberFormat,
} = require('docx');
const fs = require('fs');

// ── Data ──
const monthlyData = [
  { month: '2025-06', label: '2025年6月', total: 8089, ios: 7084, android: 817, qrScan: 38, referral: 0, googleMaps: 10, socialOther: 140, organicTotal: 7939, marketingTotal: 150, organicPct: 98.1, marketingPct: 1.9 },
  { month: '2025-07', label: '2025年7月', total: 23191, ios: 18552, android: 1999, qrScan: 270, referral: 0, googleMaps: 140, socialOther: 2230, organicTotal: 20821, marketingTotal: 2370, organicPct: 89.8, marketingPct: 10.2 },
  { month: '2025-08', label: '2025年8月', total: 24570, ios: 19530, android: 1984, qrScan: 544, referral: 340, googleMaps: 162, socialOther: 2010, organicTotal: 22058, marketingTotal: 2512, organicPct: 89.8, marketingPct: 10.2 },
  { month: '2025-09', label: '2025年9月', total: 27876, ios: 19541, android: 2243, qrScan: 909, referral: 2137, googleMaps: 323, socialOther: 2723, organicTotal: 22693, marketingTotal: 5183, organicPct: 81.4, marketingPct: 18.6 },
  { month: '2025-10', label: '2025年10月', total: 21993, ios: 14558, android: 1754, qrScan: 1067, referral: 2162, googleMaps: 301, socialOther: 2151, organicTotal: 17379, marketingTotal: 4614, organicPct: 79.0, marketingPct: 21.0 },
  { month: '2025-11', label: '2025年11月', total: 17506, ios: 11556, android: 1452, qrScan: 469, referral: 1615, googleMaps: 238, socialOther: 2176, organicTotal: 13477, marketingTotal: 4029, organicPct: 77.0, marketingPct: 23.0 },
  { month: '2025-12', label: '2025年12月', total: 22704, ios: 14989, android: 1881, qrScan: 813, referral: 1981, googleMaps: 309, socialOther: 2731, organicTotal: 17683, marketingTotal: 5021, organicPct: 77.9, marketingPct: 22.1 },
  { month: '2026-01', label: '2026年1月', total: 19226, ios: 12520, android: 1530, qrScan: 551, referral: 1549, googleMaps: 274, socialOther: 2802, organicTotal: 14601, marketingTotal: 4625, organicPct: 75.9, marketingPct: 24.1 },
  { month: '2026-02', label: '2026年2月', total: 18121, ios: 11768, android: 1338, qrScan: 1858, referral: 1356, googleMaps: 266, socialOther: 1535, organicTotal: 14964, marketingTotal: 3157, organicPct: 82.6, marketingPct: 17.4 },
  { month: '2026-03', label: '2026年3月', total: 22103, ios: 14567, android: 1550, qrScan: 2081, referral: 1557, googleMaps: 317, socialOther: 2031, organicTotal: 18198, marketingTotal: 3905, organicPct: 82.3, marketingPct: 17.7 },
];

// ── Colors ──
const NAVY = '1F4E79';
const BLUE = '2E75B6';
const TEXT = '2C3E50';
const BORDER = 'BFBFBF';
const ALT_ROW = 'F2F2F2';
const WHITE = 'FFFFFF';
const ACCENT = '0365C0';

// ── Helpers ──
const fmt = (n) => n.toLocaleString('en-US');
const heading1 = (text) => new Paragraph({
  children: [new TextRun({ text, bold: true, size: 32, color: NAVY, font: 'Arial' })],
  spacing: { before: 400, after: 200 },
});
const heading2 = (text) => new Paragraph({
  children: [new TextRun({ text, bold: true, size: 26, color: BLUE, font: 'Arial' })],
  spacing: { before: 300, after: 150 },
});
const bodyText = (text) => new Paragraph({
  children: [new TextRun({ text, size: 22, color: TEXT, font: 'Arial' })],
  spacing: { after: 120 },
  alignment: AlignmentType.JUSTIFIED,
});
const bulletText = (text) => new Paragraph({
  children: [new TextRun({ text, size: 22, color: TEXT, font: 'Arial' })],
  spacing: { after: 80 },
  bullet: { level: 0 },
});
const emptyLine = () => new Paragraph({ spacing: { after: 100 } });

// ── Table Helpers ──
const cellBorders = {
  top: { style: BorderStyle.SINGLE, size: 1, color: BORDER },
  bottom: { style: BorderStyle.SINGLE, size: 1, color: BORDER },
  left: { style: BorderStyle.SINGLE, size: 1, color: BORDER },
  right: { style: BorderStyle.SINGLE, size: 1, color: BORDER },
};

function headerCell(text, width) {
  return new TableCell({
    children: [new Paragraph({
      children: [new TextRun({ text, bold: true, size: 18, color: WHITE, font: 'Arial' })],
      alignment: AlignmentType.CENTER,
    })],
    width: { size: width || 1000, type: WidthType.DXA },
    shading: { type: ShadingType.SOLID, color: NAVY },
    borders: cellBorders,
    verticalAlign: 'center',
  });
}

function dataCell(text, shaded, align) {
  return new TableCell({
    children: [new Paragraph({
      children: [new TextRun({ text: String(text), size: 18, color: TEXT, font: 'Arial' })],
      alignment: align || AlignmentType.CENTER,
    })],
    shading: shaded ? { type: ShadingType.SOLID, color: ALT_ROW } : undefined,
    borders: cellBorders,
    verticalAlign: 'center',
  });
}

// ── Build Document ──
function buildDoc() {
  const grandTotal = 205379;
  const grandMkt = 35566;
  const grandMktPct = 17.3;
  const latestMktPct = 17.7;
  const prevMktPct = 17.4;

  // Cover page
  const coverSection = {
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 720, bottom: 720, left: 900, right: 900 },
      },
    },
    children: [
      emptyLine(), emptyLine(), emptyLine(), emptyLine(), emptyLine(), emptyLine(),
      new Paragraph({
        children: [new TextRun({ text: '━'.repeat(50), color: ACCENT, size: 20 })],
        alignment: AlignmentType.CENTER,
      }),
      emptyLine(),
      new Paragraph({
        children: [new TextRun({ text: '渠道流量贡献分析报告', bold: true, size: 52, color: NAVY, font: 'Arial' })],
        alignment: AlignmentType.CENTER, spacing: { after: 100 },
      }),
      new Paragraph({
        children: [new TextRun({ text: 'V2 · 排除法', bold: true, size: 36, color: BLUE, font: 'Arial' })],
        alignment: AlignmentType.CENTER, spacing: { after: 200 },
      }),
      new Paragraph({
        children: [new TextRun({ text: '━'.repeat(50), color: ACCENT, size: 20 })],
        alignment: AlignmentType.CENTER,
      }),
      emptyLine(), emptyLine(),
      // Doc info table
      new Table({
        rows: [
          new TableRow({ children: [headerCell('项目', 2000), headerCell('内容', 6000)] }),
          new TableRow({ children: [dataCell('编号'), dataCell('LCNA-MKT-2026-004')] }),
          new TableRow({ children: [dataCell('日期', true), dataCell('2026年3月26日', true)] }),
          new TableRow({ children: [dataCell('作者'), dataCell('曾翔宇（David Zeng）')] }),
          new TableRow({ children: [dataCell('部门', true), dataCell('DBA / Infrastructure Team', true)] }),
          new TableRow({ children: [dataCell('区域'), dataCell('北美（NA）')] }),
          new TableRow({ children: [dataCell('状态', true), dataCell('Final', true)] }),
          new TableRow({ children: [dataCell('版本'), dataCell('V2 — 基于排除法重新分析')] }),
        ],
        width: { size: 8000, type: WidthType.DXA },
        alignment: AlignmentType.CENTER,
      }),
      emptyLine(), emptyLine(),
      new Paragraph({
        children: [new TextRun({ text: '瑞幸咖啡北美 · First Ray Holdings USA Inc.', size: 22, color: '7F8C8D', font: 'Arial' })],
        alignment: AlignmentType.CENTER,
      }),
    ],
  };

  // Main content section
  const contentSection = {
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 720, bottom: 720, left: 900, right: 900 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [new TextRun({ text: 'LCNA-MKT-2026-004 | 渠道流量贡献分析（V2·排除法）', size: 16, color: '999999', font: 'Arial' })],
          alignment: AlignmentType.RIGHT,
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [new TextRun({ text: '曾翔宇 · DBA Team · 瑞幸咖啡北美 · 2026-03-26', size: 16, color: '999999', font: 'Arial' })],
          alignment: AlignmentType.CENTER,
        })],
      }),
    },
    children: [
      // 一、报告摘要
      heading1('一、报告摘要'),
      heading2('1.1 需求变更说明'),
      bodyText('Mai Shi（营销总监）于2026年3月24日会议中提出新的分析口径要求。原V1报告的"线上83.4% / 线下16.6%"分类被认为过于粗糙——83.4%的"线上"中大部分是App Store自然搜索下载，营销团队并未直接驱动。Mai要求使用排除法（Exclusion Method）重新计算营销团队的实际贡献占比。'),
      heading2('1.2 核心结论'),
      bulletText(`累计分析期间：2025年6月至2026年3月，共10个月`),
      bulletText(`总注册用户：${fmt(grandTotal)}人`),
      bulletText(`营销团队可归因占比：${grandMktPct}%（排除法下限估算）`),
      bulletText(`最新月份（2026年3月）：营销贡献占比 ${latestMktPct}%，环比上升 +${(latestMktPct - prevMktPct).toFixed(1)}pp`),
      bulletText(`趋势：营销贡献从2025年6月的1.9%增长至2026年1月的24.1%峰值，随后回落至17-18%区间`),
      heading2('1.3 方法论变更'),
      bodyText('不再使用"线上/线下"分类。改用排除法：从总量中排除营销团队明确未影响的渠道（iOS/Android有机下载 + 门店QR扫码），剩余部分归因于营销团队。此方法产生的是下限估算——实际营销贡献可能更高。'),

      // 二、排除法分析方法
      heading1('二、排除法分析方法'),
      bodyText('排除法的核心逻辑：总注册量 = 100%，减去营销团队明确未影响的渠道，剩余 = 营销团队可归因渠道。'),
      heading2('2.1 自然/门店渠道（排除项）'),
      bulletText('iOS App Store有机下载（origin=6）：用户主动在App Store搜索"Luckin"下载，营销未直接驱动'),
      bulletText('Android Google Play有机下载（origin=5）：同上逻辑'),
      bulletText('门店QR扫码（origin=4子集）：用户在门店内扫描二维码注册，属门店自然流量'),
      heading2('2.2 营销可归因渠道（余量）'),
      bulletText('好友推荐/邀请（通过t_invitation_record确认）：推荐裂变是营销团队主导的增长策略'),
      bulletText('Google Maps（CDP样本估算~5.3%）：营销团队维护Google Business Profile'),
      bulletText('社媒/红人/其他H5流量（残差）：包括TikTok、Instagram、小红书等社媒营销触达'),
      heading2('2.3 为何是下限估算'),
      bodyText('部分iOS/Android下载实际由营销驱动——例如用户看到TikTok视频后去App Store搜索下载。但由于未部署Adjust SDK等移动归因工具，无法将这部分从有机下载中分离。因此，当前的营销占比是保守的下限估算。'),

      // 三、月度渠道贡献明细
      heading1('三、月度渠道贡献明细'),
      bodyText('以下为2025年6月至2026年3月的月度渠道归因明细表：'),
      emptyLine(),
      // Main data table
      new Table({
        rows: [
          new TableRow({
            children: [
              headerCell('月份', 1200),
              headerCell('总量', 900),
              headerCell('iOS有机', 900),
              headerCell('Android', 900),
              headerCell('QR扫码*', 900),
              headerCell('推荐', 900),
              headerCell('地图*', 800),
              headerCell('社媒/其他', 1000),
              headerCell('营销占比', 1000),
            ],
          }),
          ...monthlyData.map((d, i) => new TableRow({
            children: [
              dataCell(d.label, i % 2 === 1),
              dataCell(fmt(d.total), i % 2 === 1),
              dataCell(fmt(d.ios), i % 2 === 1),
              dataCell(fmt(d.android), i % 2 === 1),
              dataCell(fmt(d.qrScan), i % 2 === 1),
              dataCell(fmt(d.referral), i % 2 === 1),
              dataCell(fmt(d.googleMaps), i % 2 === 1),
              dataCell(fmt(d.socialOther), i % 2 === 1),
              dataCell(`${d.marketingPct.toFixed(1)}%`, i % 2 === 1),
            ],
          })),
          // Grand total
          new TableRow({
            children: [
              headerCell('合计', 1200),
              headerCell(fmt(grandTotal), 900),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.ios, 0)), 900),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.android, 0)), 900),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.qrScan, 0)), 900),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.referral, 0)), 900),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.googleMaps, 0)), 800),
              headerCell(fmt(monthlyData.reduce((s, d) => s + d.socialOther, 0)), 1000),
              headerCell(`${grandMktPct}%`, 1000),
            ],
          }),
        ],
        width: { size: 10400, type: WidthType.DXA },
      }),
      emptyLine(),
      bodyText('* QR扫码通过时间代理模型估算（Model B保守估计）；Google Maps基于CDP单日样本（5.3%）估算。'),

      heading2('3.1 趋势分析'),
      bodyText('营销贡献占比呈现三个阶段：'),
      bulletText('起步期（2025年6-8月）：1.9% → 10.2%。推荐计划尚未启动，营销贡献主要来自社媒和H5渠道。'),
      bulletText('快速增长期（2025年9月-2026年1月）：18.6% → 24.1%。推荐计划全面铺开（月均2,000+邀请用户），社媒营销同步发力。'),
      bulletText('调整期（2026年2-3月）：17.4% - 17.7%。QR扫码估算值上升（门店自然流量增长），导致营销占比在排除法下有所回落。'),

      // 四、时间代理模型
      heading1('四、时间代理模型（QR扫码估算）'),
      bodyText('由于数据库中无直接的QR扫码字段，使用时间代理模型估算门店QR扫码用户数量。'),
      heading2('4.1 模型原理'),
      bodyText('QR扫码用户在门店内注册，注册后立即下单。因此，注册到首单时间≤15分钟的比率显著高于线上渠道用户。通过比较H5非推荐用户与iOS用户的15分钟下单率差异，可估算QR扫码用户占比。'),
      heading2('4.2 混合模型公式'),
      bodyText('observed_rate = x × 0.97 + (1-x) × iOS_baseline'),
      bodyText('其中：observed_rate = H5非推荐用户的15分钟下单率；iOS_baseline = iOS用户的15分钟下单率（按月计算）；0.97 = QR扫码用户的预期15分钟下单率；x = QR扫码用户占比。'),
      heading2('4.3 月度模型参数'),
      emptyLine(),
      new Table({
        rows: [
          new TableRow({
            children: [
              headerCell('月份', 1500),
              headerCell('H5非推荐15min率', 2000),
              headerCell('iOS基线', 1500),
              headerCell('QR占比(x)', 1500),
              headerCell('QR估算人数', 1500),
            ],
          }),
          ...monthlyData.filter(d => d.month >= '2025-07').map((d, i) => {
            const rates = [
              { m: '2025-07', hr: '70.2%', ir: '67.1%', qr: '10.2%' },
              { m: '2025-08', hr: '78.0%', ir: '73.3%', qr: '20.1%' },
              { m: '2025-09', hr: '79.8%', ir: '74.7%', qr: '23.0%' },
              { m: '2025-10', hr: '83.0%', ir: '76.9%', qr: '30.3%' },
              { m: '2025-11', hr: '82.7%', ir: '79.9%', qr: '16.3%' },
              { m: '2025-12', hr: '83.6%', ir: '80.0%', qr: '21.1%' },
              { m: '2026-01', hr: '83.5%', ir: '81.1%', qr: '15.2%' },
              { m: '2026-02', hr: '89.7%', ir: '82.1%', qr: '50.8%' },
              { m: '2026-03', hr: '90.7%', ir: '85.2%', qr: '47.0%' },
            ].find(r => r.m === d.month) || {};
            return new TableRow({
              children: [
                dataCell(d.label, i % 2 === 1),
                dataCell(rates.hr || 'N/A', i % 2 === 1),
                dataCell(rates.ir || 'N/A', i % 2 === 1),
                dataCell(rates.qr || 'N/A', i % 2 === 1),
                dataCell(fmt(d.qrScan), i % 2 === 1),
              ],
            });
          }),
        ],
        width: { size: 8000, type: WidthType.DXA },
      }),
      emptyLine(),
      bodyText('注：2025年6月数据量极小（188 H5用户），模型稳定性不足，仅供参考。'),

      // 五、已知局限
      heading1('五、已知局限与数据缺口'),
      bulletText('App Store/Play Store付费与有机无法区分：需部署Adjust SDK或类似移动归因工具。预计实施周期2-3个月。'),
      bulletText('QR扫码触点无法细分：门店A-frame、柜台、桌面等不同位置的扫码来源无法区分。需产品侧开发src参数埋点，预计4-6周。'),
      bulletText('Google Maps估算置信度低：当前基于2026年3月19日单日CDP样本（约20个用户），需持续积累CDP数据以提升估算精度。'),
      bulletText('营销驱动的App下载被归入有机：用户通过社媒看到广告后去App Store搜索下载，在当前方法论下被计入有机渠道。这是排除法的固有局限，也是营销占比被低估的主要原因。'),
      bulletText('2025年6-7月为早期运营阶段：门店数量少，推荐计划未启动，数据模式与后续月份差异较大。'),
      bulletText('Redshift数据暂不可用：Sensors Data事件级数据存储在Redshift中，获取访问权限后可交叉验证本分析的估算结果。'),

      // 六、行动计划
      heading1('六、行动计划'),
      heading2('6.1 短期（已完成）'),
      bulletText('交付V2排除法分析报告（LCNA-MKT-2026-004）'),
      bulletText('部署交互式仪表盘（Vercel），支持营销团队自助查看月度趋势'),
      heading2('6.2 中期（1-3个月）'),
      bulletText('部署Adjust SDK：实现App Store/Play Store付费与有机下载的精确区分'),
      bulletText('QR码src参数埋点：区分门店不同触点的扫码来源，精确度量门店自然流量'),
      bulletText('获取Redshift访问权限：使用Sensors Data事件级数据交叉验证时间代理模型'),
      bulletText('持续积累CDP数据：提升Google Maps等低置信度渠道的估算精度'),
      heading2('6.3 长期（3-6个月）'),
      bulletText('建立完整的多触点归因模型（Multi-Touch Attribution）'),
      bulletText('整合Adjust + CDP + Redshift数据，实现端到端的营销ROI追踪'),
      bulletText('自动化月度归因报告生成，替代当前的手动分析流程'),
    ],
  };

  return new Document({
    sections: [coverSection, contentSection],
  });
}

// ── Generate ──
async function main() {
  const doc = buildDoc();
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync('/home/claude/LCNA-MKT-2026-004.docx', buffer);
  console.log('DOCX report generated: /home/claude/LCNA-MKT-2026-004.docx');
  console.log(`File size: ${(buffer.length / 1024).toFixed(1)} KB`);
}

main().catch(console.error);
