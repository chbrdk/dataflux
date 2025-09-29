#!/usr/bin/env node
"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const stdio_js_1 = require("@modelcontextprotocol/sdk/server/stdio.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const axios_1 = __importDefault(require("axios"));
const ioredis_1 = __importDefault(require("ioredis"));
const zod_1 = require("zod");
const dotenv_1 = __importDefault(require("dotenv"));
// Load environment variables
dotenv_1.default.config();
// Configuration
const config = {
    ingestionServiceUrl: process.env['INGESTION_SERVICE_URL'] || 'http://localhost:8002',
    queryServiceUrl: process.env['QUERY_SERVICE_URL'] || 'http://localhost:8003',
    redisUrl: process.env['REDIS_URL'] || 'redis://localhost:2002',
    openaiApiKey: process.env['OPENAI_API_KEY'] || '',
    anthropicApiKey: process.env['ANTHROPIC_API_KEY'] || '',
    port: parseInt(process.env['PORT'] || '2015'),
};
// Initialize Redis client
const redis = new ioredis_1.default(config.redisUrl);
// HTTP client for service communication
const httpClient = axios_1.default.create({
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});
// Validation schemas
const SearchRequestSchema = zod_1.z.object({
    query: zod_1.z.string().min(1, 'Query cannot be empty'),
    media_types: zod_1.z.array(zod_1.z.string()).optional(),
    filters: zod_1.z.record(zod_1.z.any()).optional(),
    limit: zod_1.z.number().min(1).max(100).optional().default(20),
    include_segments: zod_1.z.boolean().optional().default(false),
    confidence_min: zod_1.z.number().min(0).max(1).optional().default(0.7),
});
const SimilarRequestSchema = zod_1.z.object({
    entity_id: zod_1.z.string().min(1, 'Entity ID cannot be empty'),
    threshold: zod_1.z.number().min(0).max(1).optional().default(0.75),
    limit: zod_1.z.number().min(1).max(50).optional().default(10),
    media_types: zod_1.z.array(zod_1.z.string()).optional(),
});
const AnalyzeRequestSchema = zod_1.z.object({
    entity_id: zod_1.z.string().min(1, 'Entity ID cannot be empty'),
    analysis_type: zod_1.z.enum(['summary', 'objects', 'scenes', 'transcript', 'full']).optional().default('summary'),
    include_ai_insights: zod_1.z.boolean().optional().default(true),
});
// Tool implementations
const tools = [
    {
        name: 'dataflux_search',
        description: 'Search DataFlux database for media content using natural language queries',
        inputSchema: {
            type: 'object',
            properties: {
                query: {
                    type: 'string',
                    description: 'Natural language search query (e.g., "find videos with cars", "show me images of dogs")',
                },
                media_types: {
                    type: 'array',
                    items: { type: 'string' },
                    description: 'Filter by media types: video, image, audio, document',
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of results to return (1-100)',
                    default: 20,
                },
                include_segments: {
                    type: 'boolean',
                    description: 'Include detailed segment information',
                    default: false,
                },
                confidence_min: {
                    type: 'number',
                    description: 'Minimum confidence threshold (0.0-1.0)',
                    default: 0.7,
                },
            },
            required: ['query'],
        },
    },
    {
        name: 'dataflux_analyze',
        description: 'Analyze media content and extract insights using AI',
        inputSchema: {
            type: 'object',
            properties: {
                entity_id: {
                    type: 'string',
                    description: 'ID of the media entity to analyze',
                },
                analysis_type: {
                    type: 'string',
                    enum: ['summary', 'objects', 'scenes', 'transcript', 'full'],
                    description: 'Type of analysis to perform',
                    default: 'summary',
                },
                include_ai_insights: {
                    type: 'boolean',
                    description: 'Include AI-generated insights and recommendations',
                    default: true,
                },
            },
            required: ['entity_id'],
        },
    },
    {
        name: 'dataflux_similar',
        description: 'Find similar media content based on an entity ID',
        inputSchema: {
            type: 'object',
            properties: {
                entity_id: {
                    type: 'string',
                    description: 'ID of the reference entity',
                },
                threshold: {
                    type: 'number',
                    description: 'Similarity threshold (0.0-1.0)',
                    default: 0.75,
                },
                limit: {
                    type: 'number',
                    description: 'Maximum number of similar results',
                    default: 10,
                },
                media_types: {
                    type: 'array',
                    items: { type: 'string' },
                    description: 'Filter by media types',
                },
            },
            required: ['entity_id'],
        },
    },
];
// Resource implementations
const resources = [
    {
        uri: 'dataflux://statistics',
        name: 'DataFlux Statistics',
        description: 'Current system statistics and performance metrics',
        mimeType: 'application/json',
    },
    {
        uri: 'dataflux://health',
        name: 'System Health',
        description: 'Health status of all DataFlux services',
        mimeType: 'application/json',
    },
];
// Prompt implementations
const prompts = [
    {
        name: 'analyze_video',
        description: 'Analyze a video and provide detailed insights',
        arguments: [
            {
                name: 'entity_id',
                description: 'ID of the video entity to analyze',
                required: true,
            },
            {
                name: 'focus_area',
                description: 'Specific area to focus analysis on (objects, scenes, audio, etc.)',
                required: false,
            },
        ],
    },
    {
        name: 'search_insights',
        description: 'Provide insights and recommendations based on search results',
        arguments: [
            {
                name: 'search_results',
                description: 'JSON string of search results to analyze',
                required: true,
            },
            {
                name: 'user_intent',
                description: 'Inferred user intent from the search query',
                required: false,
            },
        ],
    },
];
// Tool handlers
async function handleDatafluxSearch(args) {
    try {
        const validatedArgs = SearchRequestSchema.parse(args);
        // Call Query Service
        const response = await httpClient.post(`${config.queryServiceUrl}/api/v1/search`, validatedArgs);
        // Cache results in Redis
        const cacheKey = `search:${JSON.stringify(validatedArgs)}`;
        await redis.setex(cacheKey, 300, JSON.stringify(response.data)); // 5 min cache
        return {
            content: [
                {
                    type: 'text',
                    text: `Found ${response.data.total} results for query "${validatedArgs.query}":\n\n${JSON.stringify(response.data.results, null, 2)}`,
                },
            ],
        };
    }
    catch (error) {
        return {
            content: [
                {
                    type: 'text',
                    text: `Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
                },
            ],
            isError: true,
        };
    }
}
async function handleDatafluxAnalyze(args) {
    try {
        const validatedArgs = AnalyzeRequestSchema.parse(args);
        // Get entity details from Query Service
        const entityResponse = await httpClient.get(`${config.queryServiceUrl}/api/v1/segments/${validatedArgs.entity_id}`);
        // Generate AI insights if requested
        let aiInsights = '';
        if (validatedArgs.include_ai_insights && config.openaiApiKey) {
            try {
                const openaiResponse = await axios_1.default.post('https://api.openai.com/v1/chat/completions', {
                    model: 'gpt-4',
                    messages: [
                        {
                            role: 'system',
                            content: 'You are an AI media analyst. Provide detailed insights about media content.',
                        },
                        {
                            role: 'user',
                            content: `Analyze this media entity: ${JSON.stringify(entityResponse.data)}`,
                        },
                    ],
                    max_tokens: 500,
                }, {
                    headers: {
                        'Authorization': `Bearer ${config.openaiApiKey}`,
                        'Content-Type': 'application/json',
                    },
                });
                aiInsights = openaiResponse.data.choices[0].message.content;
            }
            catch (aiError) {
                console.warn('AI analysis failed:', aiError);
                aiInsights = 'AI analysis unavailable';
            }
        }
        return {
            content: [
                {
                    type: 'text',
                    text: `Analysis for entity ${validatedArgs.entity_id}:\n\n${JSON.stringify(entityResponse.data, null, 2)}\n\nAI Insights:\n${aiInsights}`,
                },
            ],
        };
    }
    catch (error) {
        return {
            content: [
                {
                    type: 'text',
                    text: `Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
                },
            ],
            isError: true,
        };
    }
}
async function handleDatafluxSimilar(args) {
    try {
        const validatedArgs = SimilarRequestSchema.parse(args);
        // Call Query Service
        const response = await httpClient.post(`${config.queryServiceUrl}/api/v1/similar`, validatedArgs);
        return {
            content: [
                {
                    type: 'text',
                    text: `Found ${response.data.total} similar entities for ${validatedArgs.entity_id}:\n\n${JSON.stringify(response.data.results, null, 2)}`,
                },
            ],
        };
    }
    catch (error) {
        return {
            content: [
                {
                    type: 'text',
                    text: `Similar search failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
                },
            ],
            isError: true,
        };
    }
}
// Resource handlers
async function getStatistics() {
    try {
        const response = await httpClient.get(`${config.queryServiceUrl}/api/v1/stats`);
        return {
            contents: [
                {
                    uri: 'dataflux://statistics',
                    mimeType: 'application/json',
                    text: JSON.stringify(response.data, null, 2),
                },
            ],
        };
    }
    catch (error) {
        return {
            contents: [
                {
                    uri: 'dataflux://statistics',
                    mimeType: 'application/json',
                    text: JSON.stringify({ error: 'Failed to fetch statistics' }, null, 2),
                },
            ],
        };
    }
}
async function getHealth() {
    try {
        const ingestionHealth = await httpClient.get(`${config.ingestionServiceUrl}/health`);
        const queryHealth = await httpClient.get(`${config.queryServiceUrl}/health`);
        return {
            contents: [
                {
                    uri: 'dataflux://health',
                    mimeType: 'application/json',
                    text: JSON.stringify({
                        ingestion_service: ingestionHealth.data,
                        query_service: queryHealth.data,
                        timestamp: new Date().toISOString(),
                    }, null, 2),
                },
            ],
        };
    }
    catch (error) {
        return {
            contents: [
                {
                    uri: 'dataflux://health',
                    mimeType: 'application/json',
                    text: JSON.stringify({ error: 'Failed to fetch health status' }, null, 2),
                },
            ],
        };
    }
}
// Prompt handlers
async function getAnalyzeVideoPrompt(args) {
    const { entity_id, focus_area } = args;
    const prompt = `Analyze the video with ID "${entity_id}"${focus_area ? ` focusing on ${focus_area}` : ''}.

Please provide:
1. **Content Summary**: Brief overview of the video content
2. **Key Objects**: Main objects, people, or items visible
3. **Scene Analysis**: Different scenes or segments identified
4. **Audio Elements**: Sounds, music, or speech detected
5. **Technical Details**: Video quality, duration, format
6. **Insights**: Interesting patterns, themes, or notable features

Use the dataflux_analyze tool to get detailed technical information about this video.`;
    return {
        description: `Analyze video ${entity_id}`,
        messages: [
            {
                role: 'user',
                content: {
                    type: 'text',
                    text: prompt,
                },
            },
        ],
    };
}
async function getSearchInsightsPrompt(args) {
    const { search_results, user_intent } = args;
    const prompt = `Based on these search results and the user's intent "${user_intent || 'general search'}", provide insights and recommendations:

Search Results:
${search_results}

Please provide:
1. **Result Analysis**: Summary of what was found
2. **Relevance Assessment**: How well results match the query
3. **Recommendations**: Suggestions for refining the search
4. **Related Content**: Ideas for finding similar or related content
5. **Next Steps**: Recommended actions based on the results`;
    return {
        description: 'Search insights and recommendations',
        messages: [
            {
                role: 'user',
                content: {
                    type: 'text',
                    text: prompt,
                },
            },
        ],
    };
}
// Create MCP Server
const server = new index_js_1.Server({
    name: 'dataflux-mcp-server',
    version: '1.0.0',
});
// Register tool handlers
server.setRequestHandler(types_js_1.ListToolsRequestSchema, async () => {
    return {
        tools: tools,
    };
});
server.setRequestHandler(types_js_1.CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    switch (name) {
        case 'dataflux_search':
            return await handleDatafluxSearch(args);
        case 'dataflux_analyze':
            return await handleDatafluxAnalyze(args);
        case 'dataflux_similar':
            return await handleDatafluxSimilar(args);
        default:
            throw new Error(`Unknown tool: ${name}`);
    }
});
// Register resource handlers
server.setRequestHandler(types_js_1.ListResourcesRequestSchema, async () => {
    return {
        resources: resources,
    };
});
server.setRequestHandler(types_js_1.ReadResourceRequestSchema, async (request) => {
    const { uri } = request.params;
    switch (uri) {
        case 'dataflux://statistics':
            return await getStatistics();
        case 'dataflux://health':
            return await getHealth();
        default:
            throw new Error(`Unknown resource: ${uri}`);
    }
});
// Register prompt handlers
server.setRequestHandler(types_js_1.ListPromptsRequestSchema, async () => {
    return {
        prompts: prompts,
    };
});
server.setRequestHandler(types_js_1.GetPromptRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    switch (name) {
        case 'analyze_video':
            return await getAnalyzeVideoPrompt(args);
        case 'search_insights':
            return await getSearchInsightsPrompt(args);
        default:
            throw new Error(`Unknown prompt: ${name}`);
    }
});
// Start server
async function startServer() {
    try {
        const transport = new stdio_js_1.StdioServerTransport();
        console.log('DataFlux MCP Server starting with STDIO transport');
        await server.connect(transport);
        console.log('DataFlux MCP Server connected and ready');
        // Test connections
        try {
            await redis.ping();
            console.log('✅ Redis connection established');
        }
        catch (error) {
            console.warn('⚠️ Redis connection failed:', error);
        }
        try {
            await httpClient.get(`${config.queryServiceUrl}/health`);
            console.log('✅ Query Service connection established');
        }
        catch (error) {
            console.warn('⚠️ Query Service connection failed:', error);
        }
        try {
            await httpClient.get(`${config.ingestionServiceUrl}/health`);
            console.log('✅ Ingestion Service connection established');
        }
        catch (error) {
            console.warn('⚠️ Ingestion Service connection failed:', error);
        }
    }
    catch (error) {
        console.error('Failed to start MCP server:', error);
        process.exit(1);
    }
}
// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down DataFlux MCP Server...');
    await redis.disconnect();
    process.exit(0);
});
process.on('SIGTERM', async () => {
    console.log('\nShutting down DataFlux MCP Server...');
    await redis.disconnect();
    process.exit(0);
});
// Start the server
startServer().catch(console.error);
