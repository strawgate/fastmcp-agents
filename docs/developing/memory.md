# Memory Management

Memory management in FastMCP-Agents is essential for multi-step agents to maintain context across interactions with the LLM. It involves storing and retrieving the conversation history, which is the sequence of messages exchanged during a task.

## Core Concepts

*   **Conversation History:** The chronological record of messages (system, user, assistant, tool) that an agent uses as context for generating responses and tool calls.
*   **Memory Implementation:** A component responsible for the actual storage and retrieval of the conversation history.
*   **Memory Factory:** A mechanism used by agents to obtain instances of a memory implementation. Factories control whether memory is shared or private among agent instances.

## Memory Protocol

The `MemoryProtocol` defines the standard interface for any memory implementation. It specifies the fundamental operations required to manage conversation history, such as adding messages, retrieving the history, setting the history, resetting it, and handling persistence (saving and restoring).

## Memory Factories

FastMCP-Agents provides factory patterns to control how memory instances are created and shared:

*   **`SharedMemoryFactory`:** This factory provides a single instance of a memory implementation to all agents that share the factory. Typically each Agent would have its own SharedMemoryFactory and that way all requests to the same Agent would share a conversation history.
*   **`PrivateMemoryFactory`:** This factory creates a new, independent instance of a memory implementation for each request. This ensures that every request is stateless and does not share conversation history with other requests even if they are to the same Agent.

## Memory Implementations

FastMCP-Agents offers different ways to store conversation history:

*   **`EphemeralMemory`:** This is an in-memory implementation. Conversation history is stored directly in the application's RAM and is lost when the application or server process terminates. It's suitable for short-lived tasks or debugging where persistence is not required.
*   **`DiskBackedMemory`:** This implementation is designed for persistent storage of conversation history by saving it to a file on disk. **Note: This feature is currently unimplemented and contributions are welcome.**