#!/usr/bin/env node

const neo4j = require('neo4j-driver');

const uri = process.env.NEO4J_URI || 'bolt://localhost:7687';
const username = process.env.NEO4J_USERNAME || 'neo4j';
const password = process.env.NEO4J_PASSWORD || 'bioetl_secure_password';

console.log(`Attempting connection to ${uri}...`);
console.log(`Time: ${new Date().toISOString()}`);

const driver = neo4j.driver(uri, neo4j.auth.basic(username, password), {
  disableLosslessIntegers: true,
  encryption: 'ENCRYPTION_OFF',
  connectionAcquisitionTimeout: 15000
});

driver
  .getServerInfo()
  .then((info) => {
    console.log('✅ Connection successful!');
    console.log(`Agent: ${info.agent}`);
    console.log(`Address: ${info.address}`);
    process.exit(0);
  })
  .catch((err) => {
    console.error('❌ Connection failed:', err.message);
    process.exit(1);
  });

setTimeout(() => {
  console.error('❌ Timeout after 45s');
  process.exit(1);
}, 45000);
