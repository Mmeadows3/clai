workspace "CLAI" "Domain-driven C4 model for the CLAI project." {
    model {
        lmClients = person "LM Clients" "External language model clients that discover and invoke callable tools."
        atSuite = softwareSystem "Acceptance Test Suite" "Future-state external acceptance test suite that validates server behavior through the AT API."
        toolDefinitions = softwareSystem "Tool Definitions" "Version-controlled source of tool definitions used during server startup registration."

        toolServer = softwareSystem "Tool Server" "Server that registers tools at startup and exposes a ready-to-call tool catalog." {
            startupOrchestrator = container "Startup Orchestrator" "Coordinates startup so the server reaches a ready callable state." "Startup process"
            definitionLoader = container "Tool Definition Loader" "Reads tool definitions from the tool directory source." "Registration process"
            typedMounting = container "Typed Mounting Pipeline" "Converts loaded definitions into typed, callable tool contracts." "Registration process"
            callableCatalog = container "Callable Tool Catalog" "In-memory callable catalog produced during startup registration." "Tool catalog"
            toolApi = container "Tool API" "Main API used by LM clients to discover and invoke callable tools." "MCP API"
            acceptanceTestApi = container "Acceptance Test API" "API surface used by the external acceptance test suite." "AT API"
        }

        lmClients -> toolServer "Discovers and invokes tools through" "MCP"
        atSuite -> toolServer "Validates behavior through" "AT API"
        toolDefinitions -> toolServer "Provides tool definitions during registration" "Registration input"

        toolDefinitions -> definitionLoader "Supplies definitions to" "File read"
        startupOrchestrator -> definitionLoader "Triggers loading of" "Startup control"
        definitionLoader -> typedMounting "Passes parsed definitions to" "Registration handoff"
        typedMounting -> callableCatalog "Registers callable tool contracts in" "Registration write"
        toolApi -> callableCatalog "Resolves callable tools from" "Catalog lookup"
        acceptanceTestApi -> toolApi "Exercises callable tool operations through" "AT API"

        lmClients -> toolApi "Uses callable tool operations through" "MCP"
        atSuite -> acceptanceTestApi "Runs acceptance scenarios through" "AT API"
    }

    views {
        systemContext toolServer "tool-server-system-context" {
            include lmClients
            include atSuite
            include toolDefinitions
            include toolServer
            autolayout lr
            title "Tool Server - System Context"
            description "Top-level system view showing external clients and startup input around the tool server."
        }

        container toolServer "tool-server-startup-registration" {
            include lmClients
            include atSuite
            include toolDefinitions
            include startupOrchestrator
            include definitionLoader
            include typedMounting
            include callableCatalog
            include toolApi
            include acceptanceTestApi
            autolayout lr
            title "Tool Server - Container View: Startup Registration"
            description "Container-level startup process that transforms raw tool definitions into a ready-to-call callable tool catalog."
        }

        styles {
            element "Person" {
                background #08427b
                color #ffffff
                shape person
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
        }
    }

    configuration {
        scope softwaresystem
        properties {
            "structurizr.inspection.model.softwaresystem.documentation" "ignore"
            "structurizr.inspection.model.softwaresystem.decisions" "ignore"
        }
    }
}
