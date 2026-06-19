# PostgreSQL Row Level Security (no-op on SQLite).

from django.db import migrations


def _apply_postgresql_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            CREATE SCHEMA IF NOT EXISTS app;

            CREATE OR REPLACE FUNCTION app.request_user_id() RETURNS bigint
            LANGUAGE sql
            STABLE
            AS $$
              SELECT CASE
                WHEN length(trim(coalesce(current_setting('app.request_user_id', true), ''))) = 0 THEN NULL
                ELSE trim(current_setting('app.request_user_id', true))::bigint
              END;
            $$;

            CREATE OR REPLACE FUNCTION app.request_user_is_staff() RETURNS boolean
            LANGUAGE sql
            STABLE
            AS $$
              SELECT COALESCE(
                (SELECT u.is_staff FROM accounts_user u WHERE u.id = app.request_user_id()),
                false
              );
            $$;
            """)

        # --- listings_listing ---
        cursor.execute("""
            ALTER TABLE listings_listing ENABLE ROW LEVEL SECURITY;
            ALTER TABLE listings_listing FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_listing_select ON listings_listing;
            CREATE POLICY yallastay_listing_select ON listings_listing
              FOR SELECT USING (
                app.request_user_is_staff()
                OR status = 'active'
                OR listed_by_id = app.request_user_id()
                OR (property_owner_id IS NOT NULL AND property_owner_id = app.request_user_id())
              );

            DROP POLICY IF EXISTS yallastay_listing_insert ON listings_listing;
            CREATE POLICY yallastay_listing_insert ON listings_listing
              FOR INSERT WITH CHECK (
                app.request_user_is_staff()
                OR listed_by_id = app.request_user_id()
              );

            DROP POLICY IF EXISTS yallastay_listing_update ON listings_listing;
            CREATE POLICY yallastay_listing_update ON listings_listing
              FOR UPDATE USING (
                app.request_user_is_staff()
                OR listed_by_id = app.request_user_id()
                OR (property_owner_id IS NOT NULL AND property_owner_id = app.request_user_id())
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR listed_by_id = app.request_user_id()
                OR (property_owner_id IS NOT NULL AND property_owner_id = app.request_user_id())
              );

            DROP POLICY IF EXISTS yallastay_listing_delete ON listings_listing;
            CREATE POLICY yallastay_listing_delete ON listings_listing
              FOR DELETE USING (
                app.request_user_is_staff()
                OR listed_by_id = app.request_user_id()
              );
            """)

        # --- listings_favorite ---
        cursor.execute("""
            ALTER TABLE listings_favorite ENABLE ROW LEVEL SECURITY;
            ALTER TABLE listings_favorite FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_favorite_all ON listings_favorite;
            CREATE POLICY yallastay_favorite_all ON listings_favorite
              FOR ALL USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              );
            """)

        # --- bookings_reservation ---
        cursor.execute("""
            ALTER TABLE bookings_reservation ENABLE ROW LEVEL SECURITY;
            ALTER TABLE bookings_reservation FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_reservation_all ON bookings_reservation;
            CREATE POLICY yallastay_reservation_all ON bookings_reservation
              FOR ALL USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_reservation.listing_id
                    AND l.listed_by_id = app.request_user_id()
                )
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_reservation.listing_id
                    AND l.property_owner_id IS NOT NULL
                    AND l.property_owner_id = app.request_user_id()
                )
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_reservation.listing_id
                    AND l.listed_by_id = app.request_user_id()
                )
              );
            """)

        # bookings_reservation: property_owner on listing (optional FK)
        # WITH CHECK for insert: renter creates row -> user_id = renter (OK)

        # --- bookings_viewingrequest ---
        cursor.execute("""
            ALTER TABLE bookings_viewingrequest ENABLE ROW LEVEL SECURITY;
            ALTER TABLE bookings_viewingrequest FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_viewing_all ON bookings_viewingrequest;
            CREATE POLICY yallastay_viewing_all ON bookings_viewingrequest
              FOR ALL USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_viewingrequest.listing_id
                    AND l.listed_by_id = app.request_user_id()
                )
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_viewingrequest.listing_id
                    AND l.property_owner_id IS NOT NULL
                    AND l.property_owner_id = app.request_user_id()
                )
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
                OR EXISTS (
                  SELECT 1 FROM listings_listing l
                  WHERE l.id = bookings_viewingrequest.listing_id
                    AND l.listed_by_id = app.request_user_id()
                )
              );
            """)

        # --- notifications_notification ---
        cursor.execute("""
            ALTER TABLE notifications_notification ENABLE ROW LEVEL SECURITY;
            ALTER TABLE notifications_notification FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_notification_all ON notifications_notification;
            CREATE POLICY yallastay_notification_all ON notifications_notification
              FOR ALL USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              );
            """)

        # --- reports_report ---
        cursor.execute("""
            ALTER TABLE reports_report ENABLE ROW LEVEL SECURITY;
            ALTER TABLE reports_report FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_report_all ON reports_report;
            CREATE POLICY yallastay_report_all ON reports_report
              FOR ALL USING (
                reporter_id = app.request_user_id()
                OR app.request_user_is_staff()
              )
              WITH CHECK (
                reporter_id = app.request_user_id()
                OR app.request_user_is_staff()
              );
            """)

        # --- reviews_review ---
        cursor.execute("""
            ALTER TABLE reviews_review ENABLE ROW LEVEL SECURITY;
            ALTER TABLE reviews_review FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_review_all ON reviews_review;
            CREATE POLICY yallastay_review_all ON reviews_review
              FOR ALL USING (
                app.request_user_is_staff()
                OR reviewer_id = app.request_user_id()
                OR reviewee_id = app.request_user_id()
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR reviewer_id = app.request_user_id()
              );
            """)

        # --- reviews_reviewresponse ---
        cursor.execute("""
            ALTER TABLE reviews_reviewresponse ENABLE ROW LEVEL SECURITY;
            ALTER TABLE reviews_reviewresponse FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_reviewresponse_all ON reviews_reviewresponse;
            CREATE POLICY yallastay_reviewresponse_all ON reviews_reviewresponse
              FOR ALL USING (
                app.request_user_is_staff()
                OR EXISTS (
                  SELECT 1 FROM reviews_review r
                  WHERE r.id = reviews_reviewresponse.review_id
                    AND (
                      r.reviewer_id = app.request_user_id()
                      OR r.reviewee_id = app.request_user_id()
                    )
                )
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR EXISTS (
                  SELECT 1 FROM reviews_review r
                  WHERE r.id = reviews_reviewresponse.review_id
                    AND r.reviewee_id = app.request_user_id()
                )
              );
            """)

        # --- roommates_roommateprofile ---
        cursor.execute("""
            ALTER TABLE roommates_roommateprofile ENABLE ROW LEVEL SECURITY;
            ALTER TABLE roommates_roommateprofile FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_roommateprofile_select ON roommates_roommateprofile;
            CREATE POLICY yallastay_roommateprofile_select ON roommates_roommateprofile
              FOR SELECT USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
                OR is_looking = true
              );

            DROP POLICY IF EXISTS yallastay_roommateprofile_write ON roommates_roommateprofile;
            CREATE POLICY yallastay_roommateprofile_write ON roommates_roommateprofile
              FOR INSERT WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              );

            DROP POLICY IF EXISTS yallastay_roommateprofile_update ON roommates_roommateprofile;
            CREATE POLICY yallastay_roommateprofile_update ON roommates_roommateprofile
              FOR UPDATE USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              );

            DROP POLICY IF EXISTS yallastay_roommateprofile_delete ON roommates_roommateprofile;
            CREATE POLICY yallastay_roommateprofile_delete ON roommates_roommateprofile
              FOR DELETE USING (
                app.request_user_is_staff()
                OR user_id = app.request_user_id()
              );
            """)

        # --- roommates_roommateinterest ---
        cursor.execute("""
            ALTER TABLE roommates_roommateinterest ENABLE ROW LEVEL SECURITY;
            ALTER TABLE roommates_roommateinterest FORCE ROW LEVEL SECURITY;

            DROP POLICY IF EXISTS yallastay_roommateinterest_all ON roommates_roommateinterest;
            CREATE POLICY yallastay_roommateinterest_all ON roommates_roommateinterest
              FOR ALL USING (
                app.request_user_is_staff()
                OR from_user_id = app.request_user_id()
                OR to_user_id = app.request_user_id()
              )
              WITH CHECK (
                app.request_user_is_staff()
                OR from_user_id = app.request_user_id()
                OR to_user_id = app.request_user_id()
              );
            """)


def _drop_postgresql_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        drops = [
            (
                "listings_listing",
                [
                    "yallastay_listing_select",
                    "yallastay_listing_insert",
                    "yallastay_listing_update",
                    "yallastay_listing_delete",
                ],
            ),
            ("listings_favorite", ["yallastay_favorite_all"]),
            ("bookings_reservation", ["yallastay_reservation_all"]),
            ("bookings_viewingrequest", ["yallastay_viewing_all"]),
            ("notifications_notification", ["yallastay_notification_all"]),
            ("reports_report", ["yallastay_report_all"]),
            ("reviews_review", ["yallastay_review_all"]),
            ("reviews_reviewresponse", ["yallastay_reviewresponse_all"]),
            (
                "roommates_roommateprofile",
                [
                    "yallastay_roommateprofile_select",
                    "yallastay_roommateprofile_write",
                    "yallastay_roommateprofile_update",
                    "yallastay_roommateprofile_delete",
                ],
            ),
            ("roommates_roommateinterest", ["yallastay_roommateinterest_all"]),
        ]
        for table, policies in drops:
            for pol in policies:
                cursor.execute(f"DROP POLICY IF EXISTS {pol} ON {table};")
            cursor.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
            cursor.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

        cursor.execute("""
            DROP FUNCTION IF EXISTS app.request_user_is_staff();
            DROP FUNCTION IF EXISTS app.request_user_id();
            DROP SCHEMA IF EXISTS app CASCADE;
            """)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("bookings", "0003_reservation_move_in"),
        ("listings", "0003_listing_leased_flag"),
        ("notifications", "0004_esign_and_notification_esign"),
        ("reports", "0001_initial"),
        ("reviews", "0001_initial"),
        ("roommates", "0001_initial"),
        ("esign", "0004_renter_lister_signature_images"),
    ]

    operations = [
        migrations.RunPython(_apply_postgresql_rls, _drop_postgresql_rls),
    ]
