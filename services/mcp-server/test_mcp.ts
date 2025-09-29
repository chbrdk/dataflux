#!/usr/bin/env node

import { spawn } from 'child_process';
import { writeFileSync, readFileSync } from 'fs';
import { join } from 'path';

// Test MCP Server functionality
async function testMCPServer() {
  console.log('🧪 Testing DataFlux MCP Server');
  console.log('='.repeat(40));

  const serverPath = join(process.cwd(), 'dist', 'index_simple.js');
  
  // Test 1: List Tools
  console.log('\n📋 Test 1: List Tools');
  const listToolsRequest = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
    params: {}
  };
  
  await testMCPRequest(serverPath, listToolsRequest);

  // Test 2: List Resources
  console.log('\n📋 Test 2: List Resources');
  const listResourcesRequest = {
    jsonrpc: '2.0',
    id: 2,
    method: 'resources/list',
    params: {}
  };
  
  await testMCPRequest(serverPath, listResourcesRequest);

  // Test 3: List Prompts
  console.log('\n📋 Test 3: List Prompts');
  const listPromptsRequest = {
    jsonrpc: '2.0',
    id: 3,
    method: 'prompts/list',
    params: {}
  };
  
  await testMCPRequest(serverPath, listPromptsRequest);

  // Test 4: Call Search Tool
  console.log('\n🔍 Test 4: Call Search Tool');
  const searchRequest = {
    jsonrpc: '2.0',
    id: 4,
    method: 'tools/call',
    params: {
      name: 'dataflux_search',
      arguments: {
        query: 'find videos with cars',
        limit: 5,
        include_segments: true
      }
    }
  };
  
  await testMCPRequest(serverPath, searchRequest);

  // Test 5: Call Similar Tool
  console.log('\n🔗 Test 5: Call Similar Tool');
  const similarRequest = {
    jsonrpc: '2.0',
    id: 5,
    method: 'tools/call',
    params: {
      name: 'dataflux_similar',
      arguments: {
        entity_id: 'test-entity-123',
        threshold: 0.75,
        limit: 3
      }
    }
  };
  
  await testMCPRequest(serverPath, similarRequest);

  // Test 6: Read Statistics Resource
  console.log('\n📊 Test 6: Read Statistics Resource');
  const statsRequest = {
    jsonrpc: '2.0',
    id: 6,
    method: 'resources/read',
    params: {
      uri: 'dataflux://statistics'
    }
  };
  
  await testMCPRequest(serverPath, statsRequest);

  console.log('\n🎉 All MCP Server tests completed!');
}

async function testMCPRequest(serverPath: string, request: any) {
  return new Promise((resolve, reject) => {
    const server = spawn('node', [serverPath], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    server.stdout.on('data', (data) => {
      output += data.toString();
    });

    server.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    server.on('close', (code) => {
      if (code === 0) {
        try {
          const response = JSON.parse(output);
          console.log(`✅ Request ${request.id}: ${request.method}`);
          console.log(`   Response: ${JSON.stringify(response, null, 2)}`);
        } catch (parseError) {
          console.log(`⚠️ Request ${request.id}: ${request.method}`);
          console.log(`   Raw output: ${output}`);
        }
        resolve(output);
      } else {
        console.log(`❌ Request ${request.id}: ${request.method}`);
        console.log(`   Error: ${errorOutput}`);
        reject(new Error(`Server exited with code ${code}`));
      }
    });

    // Send request to server
    server.stdin.write(JSON.stringify(request) + '\n');
    server.stdin.end();

    // Timeout after 10 seconds
    setTimeout(() => {
      server.kill();
      reject(new Error('Request timeout'));
    }, 10000);
  });
}

// Run tests
testMCPServer().catch(console.error);
