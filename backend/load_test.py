import time

from database import SessionLocal
from models import Competitor
from scheduler import check_single_competitor


# =========================================================
# CONFIGURATION
# =========================================================

NUMBER_OF_TEST_SITES = 100


# =========================================================
# CREATE TEST COMPETITORS
# =========================================================

def create_test_competitors():

    db = SessionLocal()

    try:

        print("=" * 60)
        print(
            f"Creating {NUMBER_OF_TEST_SITES} "
            f"load-test competitors"
        )
        print("=" * 60)

        competitors = []

        for i in range(
            1,
            NUMBER_OF_TEST_SITES + 1
        ):

            competitor = Competitor(
                name=f"LoadTest-{i:03d}",
                website_url="https://example.com",
                blog_url="https://example.com",
                monitoring_enabled=True,
                status="unknown"
            )

            db.add(competitor)

            competitors.append(
                competitor
            )

        db.commit()

        for competitor in competitors:
            db.refresh(competitor)

        competitor_ids = [
            competitor.id
            for competitor in competitors
        ]

        print(
            f"Created "
            f"{len(competitor_ids)} competitors"
        )

        return competitor_ids

    finally:

        db.close()


# =========================================================
# RUN LOAD TEST
# =========================================================

def run_load_test(
    competitor_ids
):

    print()
    print("=" * 60)
    print(
        f"STARTING 100-SITE LOAD TEST"
    )
    print("=" * 60)

    start_time = time.perf_counter()

    results = []

    # -----------------------------------------------------
    # Run competitors using the SAME worker function
    # used by the production scheduler.
    # -----------------------------------------------------

    from concurrent.futures import (
        ThreadPoolExecutor,
        as_completed
    )

    MAX_WORKERS = 10

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(
                check_single_competitor,
                competitor_id
            ): competitor_id
            for competitor_id in competitor_ids
        }

        for future in as_completed(
            futures
        ):

            competitor_id = futures[
                future
            ]

            try:

                result = future.result()

                results.append(
                    result
                )

            except Exception as e:

                results.append({
                    "competitor_id":
                        competitor_id,
                    "success": False,
                    "new_articles": 0,
                    "error": str(e)
                })

    total_time = (
        time.perf_counter()
        - start_time
    )

    # =====================================================
    # STATISTICS
    # =====================================================

    total = len(results)

    successful = sum(
        1
        for result in results
        if result.get("success")
    )

    failed = sum(
        1
        for result in results
        if not result.get("success")
    )

    total_articles = sum(
        result.get(
            "new_articles",
            0
        )
        for result in results
    )

    print()
    print("=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    print(
        f"Total competitors : {total}"
    )

    print(
        f"Concurrent workers: {MAX_WORKERS}"
    )

    print(
        f"Successful checks : {successful}"
    )

    print(
        f"Failed checks     : {failed}"
    )

    print(
        f"New articles      : {total_articles}"
    )

    print(
        f"Total cycle time  : "
        f"{total_time:.2f} seconds"
    )

    if total > 0:

        print(
            f"Average time/site : "
            f"{total_time / total:.2f} seconds"
        )

    print("=" * 60)

    return results


# =========================================================
# CLEANUP
# =========================================================

def cleanup_test_competitors():

    db = SessionLocal()

    try:

        test_competitors = (
            db.query(Competitor)
            .filter(
                Competitor.name.like(
                    "LoadTest-%"
                )
            )
            .all()
        )

        count = len(
            test_competitors
        )

        for competitor in test_competitors:

            db.delete(
                competitor
            )

        db.commit()

        print(
            f"Cleaned up "
            f"{count} load-test competitors"
        )

    finally:

        db.close()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    competitor_ids = []

    try:

        competitor_ids = (
            create_test_competitors()
        )

        run_load_test(
            competitor_ids
        )

    finally:

        cleanup_test_competitors()