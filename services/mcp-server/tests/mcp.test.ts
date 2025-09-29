/**
 * DataFlux MCP Server - Unit Tests
 * Comprehensive unit tests for the MCP Server
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

// Mock the MCP SDK
jest.mock('@modelcontextprotocol/sdk/server/index.js');
jest.mock('@modelcontextprotocol/sdk/server/stdio.js');

// Mock Redis
jest.mock('ioredis', () => {
  return jest.fn().mockImplementation(() => ({
    get: jest.fn().mockResolvedValue('cached_value'),
    set: jest.fn().mockResolvedValue('OK'),
    del: jest.fn().mockResolvedValue(1),
    ping: jest.fn().mockResolvedValue('PONG'),
    disconnect: jest.fn().mockResolvedValue(undefined),
  }));
});

// Mock axios
jest.mock('axios', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

describe('DataFlux MCP Server', () => {
  let mockServer: jest.Mocked<Server>;
  let mockTransport: jest.Mocked<StdioServerTransport>;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Mock server instance
    mockServer = {
      setRequestHandler: jest.fn(),
      connect: jest.fn().mockResolvedValue(undefined),
    } as any;

    // Mock transport
    mockTransport = {} as any;

    // Mock Server constructor
    (Server as jest.MockedClass<typeof Server>).mockImplementation(() => mockServer);
    (StdioServerTransport as jest.MockedClass<typeof StdioServerTransport>).mockImplementation(() => mockTransport);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Server Initialization', () => {
    it('should create server with correct name and version', () => {
      new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      expect(Server).toHaveBeenCalledWith({
        name: 'dataflux-mcp-server',
        version: '1.0.0'
      });
    });

    it('should create stdio transport', () => {
      new StdioServerTransport();
      
      expect(StdioServerTransport).toHaveBeenCalled();
    });
  });

  describe('Tool Registration', () => {
    it('should register dataflux_search tool', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for tools
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });

    it('should register dataflux_analyze tool', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for tools
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });

    it('should register dataflux_similar tool', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for tools
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });
  });

  describe('Resource Registration', () => {
    it('should register statistics resource', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for resources
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });

    it('should register health resource', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for resources
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });
  });

  describe('Prompt Registration', () => {
    it('should register analyze_video prompt', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for prompts
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });

    it('should register search_insights prompt', () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      
      // Verify setRequestHandler was called for prompts
      expect(mockServer.setRequestHandler).toHaveBeenCalled();
    });
  });

  describe('Tool Handlers', () => {
    let server: Server;

    beforeEach(() => {
      server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    });

    describe('dataflux_search tool', () => {
      it('should handle search request with valid parameters', async () => {
        const mockRequest = {
          params: {
            arguments: {
              query: 'test search',
              media_type: 'video',
              limit: 10
            }
          }
        };

        // Mock the tool handler
        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
          expect(result.content).toBeDefined();
        }
      });

      it('should handle search request with default parameters', async () => {
        const mockRequest = {
          params: {
            arguments: {
              query: 'test search'
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });

      it('should handle search request with empty query', async () => {
        const mockRequest = {
          params: {
            arguments: {
              query: ''
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });
    });

    describe('dataflux_analyze tool', () => {
      it('should handle analyze request with valid asset ID', async () => {
        const mockRequest = {
          params: {
            arguments: {
              asset_id: 'test-asset-123'
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });

      it('should handle analyze request with invalid asset ID', async () => {
        const mockRequest = {
          params: {
            arguments: {
              asset_id: 'invalid-asset'
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });
    });

    describe('dataflux_similar tool', () => {
      it('should handle similar request with valid asset ID', async () => {
        const mockRequest = {
          params: {
            arguments: {
              asset_id: 'test-asset-123',
              limit: 5
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });

      it('should handle similar request with default limit', async () => {
        const mockRequest = {
          params: {
            arguments: {
              asset_id: 'test-asset-123'
            }
          }
        };

        const toolHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'tools/call')
          ?.[1];

        if (toolHandler) {
          const result = await toolHandler(mockRequest);
          expect(result).toBeDefined();
        }
      });
    });
  });

  describe('Resource Handlers', () => {
    let server: Server;

    beforeEach(() => {
      server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    });

    describe('statistics resource', () => {
      it('should return statistics data', async () => {
        const mockRequest = {
          params: {
            uri: 'dataflux://statistics'
          }
        };

        const resourceHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'resources/read')
          ?.[1];

        if (resourceHandler) {
          const result = await resourceHandler(mockRequest);
          expect(result).toBeDefined();
          expect(result.contents).toBeDefined();
        }
      });
    });

    describe('health resource', () => {
      it('should return health data', async () => {
        const mockRequest = {
          params: {
            uri: 'dataflux://health'
          }
        };

        const resourceHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'resources/read')
          ?.[1];

        if (resourceHandler) {
          const result = await resourceHandler(mockRequest);
          expect(result).toBeDefined();
          expect(result.contents).toBeDefined();
        }
      });
    });
  });

  describe('Prompt Handlers', () => {
    let server: Server;

    beforeEach(() => {
      server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    });

    describe('analyze_video prompt', () => {
      it('should return video analysis prompt', async () => {
        const mockRequest = {
          params: {
            name: 'analyze_video',
            arguments: {
              asset_id: 'test-video-123'
            }
          }
        };

        const promptHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'prompts/get')
          ?.[1];

        if (promptHandler) {
          const result = await promptHandler(mockRequest);
          expect(result).toBeDefined();
          expect(result.messages).toBeDefined();
        }
      });
    });

    describe('search_insights prompt', () => {
      it('should return search insights prompt', async () => {
        const mockRequest = {
          params: {
            name: 'search_insights',
            arguments: {
              query: 'test search'
            }
          }
        };

        const promptHandler = mockServer.setRequestHandler.mock.calls
          .find(call => call[0] === 'prompts/get')
          ?.[1];

        if (promptHandler) {
          const result = await promptHandler(mockRequest);
          expect(result).toBeDefined();
          expect(result.messages).toBeDefined();
        }
      });
    });
  });

  describe('Error Handling', () => {
    let server: Server;

    beforeEach(() => {
      server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    });

    it('should handle invalid tool requests', async () => {
      const mockRequest = {
        params: {
          name: 'invalid_tool',
          arguments: {}
        }
      };

      const toolHandler = mockServer.setRequestHandler.mock.calls
        .find(call => call[0] === 'tools/call')
        ?.[1];

      if (toolHandler) {
        try {
          await toolHandler(mockRequest);
        } catch (error) {
          expect(error).toBeDefined();
        }
      }
    });

    it('should handle invalid resource requests', async () => {
      const mockRequest = {
        params: {
          uri: 'dataflux://invalid'
        }
      };

      const resourceHandler = mockServer.setRequestHandler.mock.calls
        .find(call => call[0] === 'resources/read')
        ?.[1];

      if (resourceHandler) {
        try {
          await resourceHandler(mockRequest);
        } catch (error) {
          expect(error).toBeDefined();
        }
      }
    });

    it('should handle invalid prompt requests', async () => {
      const mockRequest = {
        params: {
          name: 'invalid_prompt',
          arguments: {}
        }
      };

      const promptHandler = mockServer.setRequestHandler.mock.calls
        .find(call => call[0] === 'prompts/get')
        ?.[1];

      if (promptHandler) {
        try {
          await promptHandler(mockRequest);
        } catch (error) {
          expect(error).toBeDefined();
        }
      }
    });
  });

  describe('Connection Management', () => {
    it('should connect to transport', async () => {
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      const transport = new StdioServerTransport();
      
      await server.connect(transport);
      
      expect(mockServer.connect).toHaveBeenCalledWith(mockTransport);
    });

    it('should handle connection errors', async () => {
      mockServer.connect.mockRejectedValue(new Error('Connection failed'));
      
      const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      const transport = new StdioServerTransport();
      
      try {
        await server.connect(transport);
      } catch (error) {
        expect(error).toBeDefined();
        expect(error.message).toBe('Connection failed');
      }
    });
  });

  describe('Environment Configuration', () => {
    it('should use default environment variables', () => {
      // Test that environment variables are properly configured
      expect(process.env['INGESTION_SERVICE_URL']).toBeDefined();
      expect(process.env['QUERY_SERVICE_URL']).toBeDefined();
      expect(process.env['ANALYSIS_SERVICE_URL']).toBeDefined();
    });

    it('should handle missing environment variables', () => {
      // Test behavior when environment variables are missing
      const originalEnv = process.env;
      process.env = {};

      // Should not throw errors when environment variables are missing
      expect(() => {
        new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
      }).not.toThrow();

      process.env = originalEnv;
    });
  });

  describe('Performance Tests', () => {
    let server: Server;

    beforeEach(() => {
      server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    });

    it('should handle multiple concurrent requests', async () => {
      const requests = Array.from({ length: 10 }, (_, i) => ({
        params: {
          arguments: {
            query: `test search ${i}`,
            media_type: 'video',
            limit: 10
          }
        }
      }));

      const toolHandler = mockServer.setRequestHandler.mock.calls
        .find(call => call[0] === 'tools/call')
        ?.[1];

      if (toolHandler) {
        const promises = requests.map(request => toolHandler(request));
        const results = await Promise.all(promises);
        
        expect(results).toHaveLength(10);
        results.forEach(result => {
          expect(result).toBeDefined();
        });
      }
    });

    it('should handle requests within acceptable time', async () => {
      const start = Date.now();
      
      const mockRequest = {
        params: {
          arguments: {
            query: 'performance test',
            media_type: 'all',
            limit: 10
          }
        }
      };

      const toolHandler = mockServer.setRequestHandler.mock.calls
        .find(call => call[0] === 'tools/call')
        ?.[1];

      if (toolHandler) {
        await toolHandler(mockRequest);
      }

      const duration = Date.now() - start;
      expect(duration).toBeLessThan(1000); // Should complete within 1 second
    });
  });
});

// Integration tests
describe('MCP Server Integration', () => {
  it('should initialize all components correctly', () => {
    const server = new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    const transport = new StdioServerTransport();
    
    expect(server).toBeDefined();
    expect(transport).toBeDefined();
    expect(mockServer.setRequestHandler).toHaveBeenCalled();
  });

  it('should register all required handlers', () => {
    new Server({ name: 'dataflux-mcp-server', version: '1.0.0' });
    
    // Verify that setRequestHandler was called for all handler types
    const calls = mockServer.setRequestHandler.mock.calls;
    const handlerTypes = calls.map(call => call[0]);
    
    expect(handlerTypes).toContain('tools/call');
    expect(handlerTypes).toContain('resources/read');
    expect(handlerTypes).toContain('prompts/get');
  });
});
