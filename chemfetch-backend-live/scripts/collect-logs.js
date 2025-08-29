#!/usr/bin/env node
// scripts/collect-logs.js - Aggregate logs from all components

const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const outputFile = path.join(projectRoot, 'logs.txt');

function getToday() {
  return new Date().toISOString().split('T')[0];
}

function collectLogs() {
  const today = getToday();
  const allLogs = [];

  console.log('📝 Collecting logs from all ChemFetch components...');

  // 1. Backend logs
  const backendLogFile = path.join(projectRoot, 'logs', `backend-${today}.log`);
  if (fs.existsSync(backendLogFile)) {
    const backendLogs = fs.readFileSync(backendLogFile, 'utf8');
    allLogs.push(`\n=== BACKEND LOGS (${today}) ===\n${backendLogs}`);
    console.log('✅ Backend logs collected');
  } else {
    console.log('⚠️  Backend log file not found:', backendLogFile);
  }

  // 2. OCR Service logs
  const ocrLogFile = path.join(projectRoot, 'ocr_service', 'logs', `ocr-${today}.log`);
  if (fs.existsSync(ocrLogFile)) {
    const ocrLogs = fs.readFileSync(ocrLogFile, 'utf8');
    allLogs.push(`\n=== OCR SERVICE LOGS (${today}) ===\n${ocrLogs}`);
    console.log('✅ OCR logs collected');
  } else {
    console.log('⚠️  OCR log file not found:', ocrLogFile);
  }

  // 3. Client Hub logs
  const clientHubLogFile = path.join(
    projectRoot,
    '..',
    'chemfetch-client-hub-live',
    'logs',
    `client-hub-${today}.log`
  );
  if (fs.existsSync(clientHubLogFile)) {
    const clientLogs = fs.readFileSync(clientHubLogFile, 'utf8');
    allLogs.push(`\n=== CLIENT HUB LOGS (${today}) ===\n${clientLogs}`);
    console.log('✅ Client Hub logs collected');
  } else {
    console.log('⚠️  Client Hub log file not found:', clientHubLogFile);
  }

  // 4. Mobile logs (note: these are stored on device, not accessible from here)
  allLogs.push(
    `\n=== MOBILE LOGS ===\nMobile logs are stored on device at: Documents/logs/mobile-${today}.log\nAccess via app debug menu or device file system\n`
  );

  // 5. Add timestamp and system info
  const header = `ChemFetch System Logs - Generated at ${new Date().toISOString()}\n${'='.repeat(80)}\n`;

  // Write aggregated logs
  const finalLogs = header + allLogs.join('\n');
  fs.writeFileSync(outputFile, finalLogs, 'utf8');

  console.log(`\n📄 All logs aggregated to: ${outputFile}`);
  console.log(`📊 Total log size: ${(finalLogs.length / 1024).toFixed(1)}KB`);

  return outputFile;
}

if (require.main === module) {
  try {
    collectLogs();
  } catch (error) {
    console.error('❌ Failed to collect logs:', error.message);
    process.exit(1);
  }
}

module.exports = { collectLogs };
