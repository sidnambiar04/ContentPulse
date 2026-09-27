from apscheduler.schedulers.background import BackgroundScheduler

from concurrent.futures import ThreadPoolExecutor, as_completed

from datetime import datetime

from database import SessionLocal

from models import Competitor

from monitor import check_competitor


# =========================================================
# CONFIGURATION
# =========================================================

# Maximum number of competitors checked simultaneously
MAX_WORKERS = 10


# =========================================================
# SINGLE COMPETITOR WORKER
# =========================================================

def check_single_competitor(competitor_id):

    db = SessionLocal()

    try:

        competitor = (
            db.query(Competitor)
            .filter(
                Competitor.id == competitor_id
            )
            .first()
        )

        if not competitor:

            return {
                "competitor_id": competitor_id,
                "success": False,
                "new_articles": 0,
                "error": "Competitor not found"
            }

        print(
            f"Checking: {competitor.name}"
        )

        result = check_competitor(
            competitor,
            db
        )

        return {
            "competitor_id": competitor.id,

            "competitor": competitor.name,

            "success": result.get(
                "success",
                False
            ),

            "new_articles": result.get(
                "new_articles",
                0
            ),

            "error": result.get(
                "error"
            )
        }

    except Exception as e:

        print(
            f"Error checking competitor "
            f"{competitor_id}: {e}"
        )

        db.rollback()

        return {
            "competitor_id": competitor_id,
            "success": False,
            "new_articles": 0,
            "error": str(e)
        }

    finally:

        db.close()


# =========================================================
# MONITOR ALL COMPETITORS
# =========================================================

def monitor_all_competitors():

    db = SessionLocal()

    try:

        competitors = (
            db.query(Competitor)
            .filter(
                Competitor.monitoring_enabled == True
            )
            .all()
        )

        competitor_ids = [
            competitor.id
            for competitor in competitors
        ]

    finally:

        db.close()

    total = len(competitor_ids)

    print()

    print("=" * 60)

    print(
        f"[{datetime.now()}] "
        f"Checking {total} competitors"
    )

    print(
        f"Concurrent workers: {MAX_WORKERS}"
    )

    print("=" * 60)

    if total == 0:

        print(
            "No enabled competitors."
        )

        return

    # =====================================================
    # STATISTICS
    # =====================================================

    successful = 0

    failed = 0

    no_source = 0

    total_new_articles = 0

    # =====================================================
    # CONCURRENT WORKERS
    # =====================================================

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

        for future in as_completed(futures):

            competitor_id = futures[future]

            try:

                result = future.result()

                competitor_name = result.get(
                    "competitor",
                    f"ID {competitor_id}"
                )

                new_articles = result.get(
                    "new_articles",
                    0
                )

                error = result.get(
                    "error"
                )

                # =========================================
                # SUCCESS
                # =========================================

                if result.get("success"):

                    successful += 1

                    print(
                        f"✓ {competitor_name}: "
                        f"{new_articles} new articles"
                    )

                # =========================================
                # NO SOURCE
                # =========================================

                elif (
                    error is not None
                    and error.strip().lower()
                    == (
                        "no rss, sitemap, or "
                        "blog source configured"
                    )
                ):

                    no_source += 1

                    print(
                        f"⚠ {competitor_name}: "
                        f"No monitoring source configured"
                    )

                # =========================================
                # ACTUAL FAILURE
                # =========================================

                else:

                    failed += 1

                    print(
                        f"✗ {competitor_name}: "
                        f"{error}"
                    )

                total_new_articles += new_articles

            except Exception as e:

                failed += 1

                print(
                    f"✗ Worker error for "
                    f"competitor {competitor_id}: "
                    f"{e}"
                )

    # =====================================================
    # CYCLE SUMMARY
    # =====================================================

    print()

    print(
        f"Monitoring cycle complete | "
        f"Total: {total} | "
        f"Successful: {successful} | "
        f"Failed: {failed} | "
        f"No Source: {no_source} | "
        f"New articles: {total_new_articles}"
    )

    print("=" * 60)

    print()


# =========================================================
# APSCHEDULER
# =========================================================

scheduler = BackgroundScheduler()

scheduler.add_job(
    monitor_all_competitors,

    "interval",

    minutes=1,

    id="competitor_monitor",

    replace_existing=True,

    # Never allow two complete monitoring cycles
    # to execute simultaneously.
    max_instances=1,

    # If a scheduled run is missed, only execute
    # the latest missed run.
    coalesce=True,

    # Allow a 30-second grace period.
    misfire_grace_time=30
)


# =========================================================
# START SCHEDULER
# =========================================================

def start_scheduler():

    if not scheduler.running:

        scheduler.start()

        print(
            "ContentPulse scheduler started."
        )