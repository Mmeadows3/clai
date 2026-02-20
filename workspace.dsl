workspace "CLAI" "Domain-driven C4 model for the CLAI project." {
    model {
        lmClients = person "LM" "External LM actor that discovers and invokes server tools."
        toolServer = softwareSystem "Server" "MCP server that registers tools at startup and exposes callable tools."
        toolsDirectory = softwareSystem "Tools Directory" "Version-controlled ./tools directory used to bootstrap server tool registration."
        adapters = softwareSystem "Adapters" "Abstraction layer that allows acceptance test suite to operate at a level closer to DSL."
        atSuite = softwareSystem "Acceptance Test Suite" "High-level, behavior-scoped test suite for TDD."

        lmClients -> toolServer "MCP"
        toolServer -> lmClients "MCP"
        toolsDirectory -> toolServer "Bootstraps registration"
        toolsDirectory -> adapters "RO"
        adapters -> toolServer "MCP"
        toolServer -> adapters "MCP"
        atSuite -> adapters "Uses"
        adapters -> atSuite "Returns results"
    }

    views {
        systemLandscape "main-overview" {
            include lmClients
            include atSuite
            include adapters
            include toolsDirectory
            include toolServer
            autolayout lr
            title "CLAI - Main Overview"
            description "High-level architecture: LM uses MCP server, server bootstraps from ./tools, and acceptance tests run through adapters."
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
        properties {
            "structurizr.inspection.model.softwaresystem.documentation" "ignore"
            "structurizr.inspection.model.softwaresystem.decisions" "ignore"
        }
    }
}
