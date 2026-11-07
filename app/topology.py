"""Topology model. Edges must be backed by LLDP/SNMP evidence, never guessed."""

from dataclasses import dataclass


@dataclass
class TopologyEdge:
    source: str
    target: str
    evidence: str
    confidence: str = "真实"


def build_edges(_devices):
    # A plain IP scan cannot establish switch-port relationships.
    return []

