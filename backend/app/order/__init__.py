"""C3 Order (U2): order create/query/status/delete.

Customer identity (store_id/table_no) is taken ONLY from TabletContext
(INTEGRATION_CONTRACT.md v0.2.0 §4/§5.3), never from request body/query.
"""
