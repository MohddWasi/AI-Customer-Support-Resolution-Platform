# Sensitive Action Policy

The AI may suggest sensitive actions but must not execute them without an authorized workflow.

Sensitive actions include:

- refunds
- subscription changes
- account deletion
- security-setting changes
- changing user roles
- exposing private account information
- closing high-priority incidents

Required flow:

AI proposes action -> backend authorization check -> human approval when required -> tool execution -> audit log.

The LLM is not the authorization layer.
