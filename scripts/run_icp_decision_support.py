#!/usr/bin/env python3
from searchleads.icp_decision_support import acceptance_fixture_snapshot, assess_icp_readiness


def main():
    report=assess_icp_readiness(acceptance_fixture_snapshot())
    print(f"ICP_DIMENSIONS={report.total}")
    print(f"READY={report.ready}")
    print(f"PARTIAL={report.partial}")
    print(f"BLOCKED={report.blocked}")
    print("ICP_DEFINED=NO")
    print()
    for item in report.assessments:
        print(f"{item.dimension.value}={item.readiness.value}")
        print("  support=" + (", ".join(item.observed_support) if item.observed_support else "NONE"))
        for blocker in item.blockers:
            print("  blocker=" + blocker)


if __name__ == "__main__":
    main()
