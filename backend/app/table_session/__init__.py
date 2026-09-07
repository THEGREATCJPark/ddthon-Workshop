"""C4 TableSession (U2): table config setup + table-usage(order) session lifecycle.

The table-usage session (this module) is INDEPENDENT of the tablet auth session
owned by U1 (contract §9). Ending a usage session never logs out the tablet.
"""
