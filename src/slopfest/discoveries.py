from __future__ import annotations
from dataclasses import dataclass
import random
import pygame

UNIQUE_MODULES = ("Ghost Compass", "Severance Capacitor", "Mnemonic Cooler", "Slipstream Governor")

SEVERANCE_ACCOUNTS = (
    "Relay maintenance transcript 14-A: the shutdown order was authenticated by the central Wayline authority.",
    "Archive fragment, Meridian schoolbook: no central Wayline authority ever existed; each relay governed itself.",
    "Black-box recovery 7: traffic was halted after an unidentified vessel appeared simultaneously at six relay exits.",
    "Orison oral history: the network failed slowly over eleven years, not in a single night.",
    "Cobalt naval archive: synchronized relay loss occurred within ninety-two seconds across mapped human space.",
    "Anonymous engineer's journal: somebody changed the navigation constants three days before the first failures.",
    "Free Meridian customs ledger: trade continued through at least four supposedly dead relays for nineteen months.",
    "Research note R-441: the final Wayline packets were not distress calls. They were handshake requests.",
    "Recovered sermon: the Severance was deliberate quarantine, and reconnection is the dangerous part.",
    "Transit authority memo: rumors of quarantine are explicitly denied in language unusually specific for a routine memo.",
    "Relay 8K diagnostic: all systems nominal immediately before external command forced a cold shutdown.",
    "Outer Relay thesis fragment: the word 'Severance' does not appear in surviving records until eighty years after the event.",
    "Drift recorder: a vessel entered a relay corridor after shutdown and emerged with clocks running seventeen hours behind.",
    "Colonial legal record: local leaders voted to destroy their relay rather than risk reconnection with neighboring systems.",
    "Uncatalogued transmission: WE DID NOT LOSE THE WAYLINE. WE CLOSED THE DOOR.",
    "Autonomous beacon log: repeated route requests originated from a system that has no registered star.",
    "Shipyard folklore: pre-Severance hulls used an extra navigation socket whose purpose modern engineers cannot explain.",
    "Relay security audit: access keys were rotated six minutes after the network was already believed offline.",
    "Cobalt Assembly museum placard: the Severance was an unavoidable infrastructure cascade caused by human complacency.",
    "Private Cobalt memorandum: suppress all references to command-origin telemetry pending executive review.",
    "Research Outpost note: every reactivated relay is broadcasting the same low-power carrier toward galactic north.",
    "Merchant captain testimony: the first modern relay to awaken offered routes to three systems absent from all charts.",
    "Derelict crew log: navigation AI repeatedly asked whether 'containment remained morally acceptable.'",
    "Wayline firmware comment: emergency topology mode intended for isolation of infected route clusters.",
)

SITE_NAMES = {
    "Derelict": ("Drift Hull","Silent Courier","Broken Crown","Orphan Freighter","Transit Wreck","Cold Lantern"),
    "Wayline Relay": ("Relay K-19","Relay Vesper","Relay Nineglass","Relay Orpheus","Relay Cinder","Relay Morrow"),
    "Anomaly": ("Echo Scar","Null Chorus","Glass Wake","Blue Static","Clockfall","Ghost Vector"),
    "Abandoned Station": ("Depot Sable","Station Palinode","Authority Cache","Dock 47","Transit Annex","Archive Anchorage"),
}

@dataclass
class Site:
    site_id: int
    name: str
    kind: str
    pos: pygame.Vector2
    lore: str
    reward_kind: str
    reward_value: str | int
    discovered: bool = False
    visited: bool = False
    depleted: bool = False

    @property
    def action_label(self) -> str:
        if self.depleted:
            return "SITE EXHAUSTED"
        return {
            "Wayline Relay": "ACTIVATE RELAY",
            "Derelict": "SALVAGE DERELICT",
            "Abandoned Station": "SEARCH STATION",
        }.get(self.kind, "SCAN ANOMALY")

def generate_sites(planets, world_size: pygame.Vector2, rng: random.Random, count: int = 12) -> list[Site]:
    kinds = ["Derelict", "Wayline Relay", "Anomaly", "Abandoned Station"] * 3
    rng.shuffle(kinds)
    sites: list[Site] = []
    names_used: set[str] = set()

    for site_id in range(count):
        kind = kinds[site_id % len(kinds)]
        pos = None
        for _ in range(300):
            candidate = pygame.Vector2(
                rng.uniform(300, world_size.x - 300),
                rng.uniform(300, world_size.y - 300),
            )
            if any(candidate.distance_to(p.pos) < 260 for p in planets):
                continue
            if any(candidate.distance_to(s.pos) < 340 for s in sites):
                continue
            pos = candidate
            break
        if pos is None:
            pos = pygame.Vector2(400 + site_id * 250, 500 + (site_id % 5) * 500)

        available = [n for n in SITE_NAMES[kind] if n not in names_used]
        name = rng.choice(available or SITE_NAMES[kind])
        names_used.add(name)
        lore = SEVERANCE_ACCOUNTS[site_id % len(SEVERANCE_ACCOUNTS)]

        if kind == "Wayline Relay":
            reward_kind, reward_value = "relay", 1
        elif kind == "Derelict" and site_id % 2 == 0:
            reward_kind, reward_value = "module", UNIQUE_MODULES[(site_id // 2) % len(UNIQUE_MODULES)]
        elif kind == "Abandoned Station" and site_id % 3 == 0:
            reward_kind, reward_value = "weapon", "Relay Lance"
        elif kind == "Anomaly":
            reward_kind, reward_value = "artifact", 2
        else:
            reward_kind, reward_value = "credits", 110 + site_id * 13

        sites.append(Site(site_id, name, kind, pos, lore, reward_kind, reward_value))
    return sites
