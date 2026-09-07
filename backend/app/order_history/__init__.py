"""C5 OrderHistory (U2): archive of ended usage sessions + history queries.

Records are immutable. Each archived record preserves the original order time
(`ordered_at` = snapshot of orders.created_at) and the usage-completion time
(`completed_at`) per contract v0.2.0 §3/§5.4.
"""
