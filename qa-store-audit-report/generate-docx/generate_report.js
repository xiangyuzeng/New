#!/usr/bin/env node
/**
 * QA Store Audit Monthly Analysis — DOCX Report Generator.
 * Reads JSON analysis results, generates a styled .docx report.
 *
 * Usage:
 *   node generate_report.js <path_to_analysis_json> [output_dir]
 */

const fs = require('fs');
const path = require('path');
const { Document, Packer } = require('docx');

const { documentStyles } = require('./styles');
const { buildCoverPage } = require('./sections/cover_page');
const { buildDocInfo } = require('./sections/doc_info');
const { buildSection1 } = require('./sections/section1_overview');
const { buildSection2 } = require('./sections/section2_modules');
const { buildSection3 } = require('./sections/section3_risk');
const { buildSection4 } = require('./sections/section4_correlation');
const { buildSection5 } = require('./sections/section5_capa');
const { buildSection6 } = require('./sections/section6_actions');

async function main() {
  const inputPath = process.argv[2];
  const outputDirArg = process.argv[3];

  if (!inputPath) {
    console.error('Usage: node generate_report.js <path_to_analysis_json> [output_dir]');
    console.error('');
    console.error('  Reads JSON from Python analysis stage and generates .docx report.');
    process.exit(1);
  }

  if (!fs.existsSync(inputPath)) {
    console.error(`ERROR: Input file not found: ${inputPath}`);
    process.exit(1);
  }

  // Read JSON
  console.log(`Reading analysis JSON: ${inputPath}`);
  const raw = fs.readFileSync(inputPath, 'utf-8');
  const data = JSON.parse(raw);
  const { metadata } = data;

  console.log(`Report: ${metadata.report_id} — ${metadata.analysis_month_cn}`);
  console.log(`  Stores: ${metadata.total_stores}, Inspections: ${metadata.total_inspections}`);

  // Build document
  const doc = new Document({
    creator: metadata.author,
    title: `QA门店巡检月度分析报告 ${metadata.analysis_month_cn}`,
    description: `Monthly QA Store Audit Analysis Report — ${metadata.analysis_month}`,
    styles: documentStyles(),
    sections: [
      buildCoverPage(metadata),
      buildDocInfo(metadata),
      buildSection1(data.layer1_store_performance, metadata),
      buildSection2(data.layer2_module_analysis, metadata),
      buildSection3(data.layer3_risk_analysis, metadata),
      buildSection4(data.layer2_module_analysis, data.layer1_store_performance, metadata),
      buildSection5(data.layer4_capa, metadata),
      buildSection6(data, metadata),
    ],
  });

  // Generate output
  const outputDir = outputDirArg || path.dirname(inputPath);
  const monthStr = metadata.analysis_month.replace('-', '年') + '月';
  const outputName = `QA门店巡检月度分析报告_${monthStr}.docx`;
  const outputPath = path.join(outputDir, outputName);

  console.log(`Generating DOCX: ${outputPath}`);
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);

  const sizeMB = (buffer.length / 1024 / 1024).toFixed(2);
  console.log(`Done! Report generated: ${outputPath} (${sizeMB} MB)`);

  return outputPath;
}

main().catch(err => {
  console.error('ERROR generating report:', err.message);
  console.error(err.stack);
  process.exit(1);
});
