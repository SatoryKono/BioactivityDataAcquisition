#!/usr/bin/env node

/**
 * MCP Server for Neo4j Memory Management
 * Provides tools for monitoring and optimizing Neo4j memory configuration
 */

import Anthropic from "@anthropic-ai/sdk";
import { exec } from "child_process";
import { promisify } from "util";
import * as fs from "fs";
import * as path from "path";

const execAsync = promisify(exec);

// Initialize the client
const client = new Anthropic();

const MODEL_ID = "claude-3-5-sonnet-20241022";

// Memory storage file path
const MEMORY_FILE_PATH =
  process.env.MEMORY_FILE_PATH ||
  ".ai/mcp/neo4j-memory/memory.json";

// Tool definitions
const tools = [
  {
    name: "get_memory_profile",
    description:
      "Get the current Neo4j memory profile configuration (development, staging, production)",
    input_schema: {
      type: "object",
      properties: {
        profile: {
          type: "string",
          enum: ["development", "staging", "production"],
          description: "The memory profile to retrieve",
        },
      },
      required: ["profile"],
    },
  },
  {
    name: "get_current_configuration",
    description: "Get the current Neo4j memory configuration settings",
    input_schema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "check_neo4j_health",
    description: "Check the current health status and memory usage of Neo4j container",
    input_schema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "get_memory_allocation_rules",
    description:
      "Get the rules for allocating memory (heap, pagecache, OS buffer)",
    input_schema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "recommend_configuration",
    description:
      "Get recommended Neo4j memory configuration based on available host RAM",
    input_schema: {
      type: "object",
      properties: {
        available_ram_gb: {
          type: "number",
          description: "Available host RAM in GB",
        },
      },
      required: ["available_ram_gb"],
    },
  },
  {
    name: "update_memory_profile",
    description: "Update the current memory profile in the memory storage",
    input_schema: {
      type: "object",
      properties: {
        profile: {
          type: "string",
          enum: ["development", "staging", "production"],
          description: "The memory profile to set as current",
        },
      },
      required: ["profile"],
    },
  },
  {
    name: "save_custom_configuration",
    description: "Save a custom Neo4j memory configuration",
    input_schema: {
      type: "object",
      properties: {
        name: {
          type: "string",
          description: "Configuration name",
        },
        heap_initial: {
          type: "string",
          description: "Initial heap size (e.g., '512m')",
        },
        heap_max: {
          type: "string",
          description: "Maximum heap size (e.g., '2g')",
        },
        pagecache: {
          type: "string",
          description: "Page cache size (e.g., '1g')",
        },
      },
      required: ["name", "heap_initial", "heap_max", "pagecache"],
    },
  },
  {
    name: "get_tuning_checklist",
    description: "Get the Neo4j memory tuning checklist before deployment",
    input_schema: {
      type: "object",
      properties: {},
    },
  },
];

// Tool handlers
async function handleToolCall(toolName, toolInput) {
  const memory = JSON.parse(fs.readFileSync(MEMORY_FILE_PATH, "utf8"));

  switch (toolName) {
    case "get_memory_profile":
      return memory.memory_profiles[toolInput.profile] || "Profile not found";

    case "get_current_configuration":
      return memory.current_configuration;

    case "get_memory_allocation_rules":
      return memory.memory_allocation_rules;

    case "check_neo4j_health":
      try {
        const { stdout } = await execAsync(
          "docker compose ps neo4j --format json"
        );
        const containers = JSON.parse(stdout);
        const neo4j = containers.find((c) => c.Service === "neo4j");
        if (!neo4j) {
          return "Neo4j container not found";
        }
        const statsOutput = await execAsync("docker stats bioetl-neo4j --no-stream --format json");
        const stats = JSON.parse(statsOutput.stdout)[0];
        return {
          status: neo4j.State,
          health: neo4j.Health || "N/A",
          memory_usage: stats.MemUsage,
          memory_percent: stats.MemPerc,
        };
      } catch (error) {
        return `Error checking health: ${error.message}`;
      }

    case "recommend_configuration":
      const ramGB = toolInput.available_ram_gb;
      return {
        recommendation: `Based on ${ramGB}GB available RAM:`,
        heap_max: `${Math.floor(ramGB * 0.35)}g`,
        heap_initial: `${Math.floor(ramGB * 0.1)}g`,
        pagecache: `${Math.floor(ramGB * 0.45)}g`,
        os_reserve: `${Math.floor(ramGB * 0.1)}g`,
        rationale:
          "Heap 35%, PageCache 45%, OS Reserve 20% allocation",
      };

    case "update_memory_profile":
      memory.current_configuration = {
        ...memory.current_configuration,
        environment: toolInput.profile,
        ...memory.memory_profiles[toolInput.profile],
      };
      fs.writeFileSync(MEMORY_FILE_PATH, JSON.stringify(memory, null, 2));
      return `Memory profile updated to: ${toolInput.profile}`;

    case "save_custom_configuration":
      if (!memory.custom_configurations) {
        memory.custom_configurations = {};
      }
      memory.custom_configurations[toolInput.name] = {
        heap_initial: toolInput.heap_initial,
        heap_max: toolInput.heap_max,
        pagecache: toolInput.pagecache,
      };
      fs.writeFileSync(MEMORY_FILE_PATH, JSON.stringify(memory, null, 2));
      return `Custom configuration '${toolInput.name}' saved`;

    case "get_tuning_checklist":
      return memory.tuning_checklist;

    default:
      return "Unknown tool";
  }
}

// Main MCP loop
async function main() {
  const messages = [];

  // Initial system message
  const systemPrompt = `You are a Neo4j memory configuration expert. You have access to tools that help manage and optimize Neo4j memory settings. 
  
Use these tools to:
1. Analyze current memory configuration
2. Check Neo4j health and memory usage
3. Recommend optimal configurations based on available RAM
4. Help troubleshoot memory-related issues
5. Provide guidance on memory tuning for different environments (dev, staging, prod)

Always provide actionable recommendations and explain the rationale behind them.`;

  console.log("Neo4j Memory Management MCP Server initialized");
  console.log("Ready to assist with Neo4j memory configuration\n");

  // Process tool calls in a loop (simulating the MCP protocol)
  let continueLoop = true;

  while (continueLoop) {
    try {
      const userInput = await getUserInput();

      if (!userInput || userInput.toLowerCase() === "exit") {
        continueLoop = false;
        break;
      }

      messages.push({
        role: "user",
        content: userInput,
      });

      // Call Claude with tools
      const response = await client.messages.create({
        model: MODEL_ID,
        max_tokens: 4096,
        system: systemPrompt,
        tools: tools,
        messages: messages,
      });

      // Process response
      let assistantMessage = {
        role: "assistant",
        content: [],
      };

      for (const block of response.content) {
        if (block.type === "text") {
          console.log(`\nAssistant: ${block.text}\n`);
          assistantMessage.content.push({
            type: "text",
            text: block.text,
          });
        } else if (block.type === "tool_use") {
          console.log(`Using tool: ${block.name}`);
          console.log(`Input: ${JSON.stringify(block.input, null, 2)}`);

          const toolResult = await handleToolCall(block.name, block.input);
          console.log(`Result: ${JSON.stringify(toolResult, null, 2)}\n`);

          assistantMessage.content.push({
            type: "tool_use",
            id: block.id,
            name: block.name,
            input: block.input,
          });

          // Add tool result to messages
          messages.push(assistantMessage);
          messages.push({
            role: "user",
            content: [
              {
                type: "tool_result",
                tool_use_id: block.id,
                content: JSON.stringify(toolResult),
              },
            ],
          });

          // Recursively process if there are more tool calls
          continueLoop = true;
        }
      }

      // Add final assistant message if not already added
      if (!assistantMessage.content.some((c) => c.type === "tool_use")) {
        messages.push(assistantMessage);
      }
    } catch (error) {
      console.error("Error:", error.message);
    }
  }

  console.log("\nNeo4j Memory Management session ended");
}

// Helper function to get user input (simulated)
async function getUserInput() {
  return new Promise((resolve) => {
    process.stdout.write("You: ");
    let input = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (char) => {
      if (char === "\n") {
        process.stdin.pause();
        resolve(input);
      } else {
        input += char;
      }
    });
  });
}

main().catch(console.error);
