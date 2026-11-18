# Historical Ticket TKT-0004

Status: Resolved
Category: Container Registry
Priority: High

Customer message:
Docker login to our registry returns an access forbidden error.

Investigation:
The authentication request was not carrying the Authorization header required by the configured token validation endpoint.

Resolution:
The support response recommended checking proxy/reverse-proxy handling of the Authorization header.

Authoritative source:
GitLab container registry authentication documentation.

This ticket is synthetic historical data created for evaluation and demonstration.
