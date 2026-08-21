#!/usr/bin/env python3
from searchleads.icp_decision_support import acceptance_fixture_snapshot, qualification_bridge_snapshot, qualification_field_canonicalization_snapshot, assess_icp_readiness


def show(label, snapshot):
    report=assess_icp_readiness(snapshot)
    print(label)
    print(f"ICP_DIMENSIONS={report.total}")
    print(f"READY={report.ready}")
    print(f"PARTIAL={report.partial}")
    print(f"BLOCKED={report.blocked}")
    print("ICP_DEFINED=NO")
    for item in report.assessments:
        print(f"{item.dimension.value}={item.readiness.value}")
        print("  support=" + (", ".join(item.observed_support) if item.observed_support else "NONE"))
        for blocker in item.blockers:
            print("  blocker=" + blocker)
    print()


def main():
    show("BASE_ACCEPTANCE",acceptance_fixture_snapshot())
    show("WITH_QUALIFICATION_SIGNAL_BRIDGE",qualification_bridge_snapshot())
    show("WITH_FIELD_CANONICALIZATION",qualification_field_canonicalization_snapshot())


if __name__ == "__main__":
    main()
