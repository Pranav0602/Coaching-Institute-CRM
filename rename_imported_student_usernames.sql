-- Rename the imported student accounts to usernames based on each student's full name.
-- Run in pgAdmin Query Tool connected to the Render/server database.
-- Only the 129 registration numbers from STUDENT_DATA_CRM are targeted.
-- Spaces and unsupported username characters become underscores; duplicate names or
-- usernames already in use receive a numeric suffix so usernames remain unique.

BEGIN;

DO $rename_student_usernames$
DECLARE
    v_student record;
    v_full_name text;
    v_base_username text;
    v_candidate text;
    v_suffix integer;
    v_updated integer := 0;
BEGIN
    FOR v_student IN
        SELECT p.reg_no, p.user_id, u.first_name, u.last_name
          FROM public.users_profiles_studentprofile AS p
          JOIN public.accounts_user AS u ON u.id = p.user_id
          JOIN public.accounts_role AS r ON r.id = u.role_id
          JOIN (VALUES
        ('SEP26-M01'),
        ('SEP26-C02'),
        ('SEP26-C03'),
        ('SEP26-M04'),
        ('SEP26-C05'),
        ('SEP26-E06'),
        ('SEP26-E07'),
        ('SEP26-E08'),
        ('SEP26-C09'),
        ('SEP26-M10'),
        ('SEP26-M11'),
        ('SEP26-M12'),
        ('SEP26-M13'),
        ('SEP26-M14'),
        ('SEP26-M15'),
        ('SEP26-E16'),
        ('SEP26-E17'),
        ('SEP26-C18'),
        ('SEP26-C19'),
        ('SEP26-C20'),
        ('SEP26-C21'),
        ('SEP26-M22'),
        ('SEP26-M23'),
        ('SEP26-M24'),
        ('SEP26-M25'),
        ('SEP26-M26'),
        ('SEP26-M27'),
        ('SEP26-M28'),
        ('SEP26-C29'),
        ('SEP26-E30'),
        ('SEP26-E31'),
        ('SEP26-E32'),
        ('SEP26-E33'),
        ('SEP26-M34'),
        ('SEP26-C35'),
        ('SEP26-E36'),
        ('SEP26-M37'),
        ('SEP26-C38'),
        ('SEP26-C39'),
        ('SEP26-C40'),
        ('SEP26-M41'),
        ('SEP26-M42'),
        ('SEP26-E43'),
        ('SEP26-M44'),
        ('SEP26-E45'),
        ('SEP26-C46'),
        ('SEP26-C47'),
        ('SEP26-C48'),
        ('SEP26-C49'),
        ('SEP26-C50'),
        ('SEP26-E51'),
        ('SEP26-M52'),
        ('SEP26-M53'),
        ('SEP26-C54'),
        ('SEP26-M55'),
        ('SEP26-M56'),
        ('SEP26-M57'),
        ('SEP26-M58'),
        ('SEP26-C59'),
        ('SEP26-C60'),
        ('SEP26-C61'),
        ('SEP26-M62'),
        ('SEP26-M63'),
        ('SEP26-M64'),
        ('OCT26-M01'),
        ('OCT26-M02'),
        ('OCT26-C03'),
        ('OCT26-C04'),
        ('OCT26-C05'),
        ('OCT26-E06'),
        ('OCT26-E07'),
        ('OCT26-E08'),
        ('OCT26-M09'),
        ('OCT26-M10'),
        ('OCT26-M11'),
        ('OCT26-C12'),
        ('OCT26-C13'),
        ('OCT26-C14'),
        ('OCT26-C15'),
        ('OCT26-M16'),
        ('OCT26-E17'),
        ('OCT26-E18'),
        ('OCT26-E19'),
        ('OCT26-M20'),
        ('OCT26-M21'),
        ('OCT26-M22'),
        ('OCT26-M23'),
        ('OCT26-M24'),
        ('OCT26-M25'),
        ('OCT26-M26'),
        ('OCT26-M27'),
        ('OCT26-M28'),
        ('OCT26-E29'),
        ('OCT26-M30'),
        ('OCT26-M31'),
        ('OCT26-M32'),
        ('OCT26-M33'),
        ('OCT26-C34'),
        ('OCT26-C35'),
        ('OCT26-C36'),
        ('OCT26-C37'),
        ('OCT26-C38'),
        ('OCT26-C39'),
        ('OCT26-C40'),
        ('OCT26-C41'),
        ('OCT26-C42'),
        ('OCT26-M43'),
        ('OCT26-C44'),
        ('OCT26-C45'),
        ('OCT26-C46'),
        ('OCT26-C47'),
        ('OCT26-M48'),
        ('OCT26-M49'),
        ('OCT26-C50'),
        ('OCT26-C51'),
        ('OCT26-IT52'),
        ('OCT26-M53'),
        ('OCT26-M54'),
        ('OCT26-E55'),
        ('OCT26-M56'),
        ('OCT26-M57'),
        ('OCT26-M58'),
        ('OCT26-M59'),
        ('OCT26-E60'),
        ('OCT26-M61'),
        ('OCT26-M62'),
        ('OCT26-M63'),
        ('OCT26-E64'),
        ('OCT26-C65')
          ) AS roster(reg_no) ON roster.reg_no = p.reg_no
         WHERE r.code = 'STUDENT'
           AND u.is_deleted = false
           AND p.is_deleted = false
         ORDER BY p.reg_no
    LOOP
        v_full_name := nullif(
            btrim(concat_ws(
                ' ',
                nullif(btrim(v_student.first_name), ''),
                nullif(btrim(v_student.last_name), '')
            )),
            ''
        );
        IF v_full_name IS NULL THEN
            RAISE EXCEPTION 'Student % has no full name; no changes committed.', v_student.reg_no;
        END IF;

        -- Django usernames cannot contain spaces. Keep letters/numbers and its
        -- permitted punctuation, replacing other runs with underscores.
        v_base_username := lower(regexp_replace(v_full_name, '[^[:alnum:]_.@+-]+', '_', 'g'));
        v_base_username := btrim(regexp_replace(v_base_username, '_+', '_', 'g'), '_');
        IF v_base_username = '' THEN
            RAISE EXCEPTION 'Student % has no usable username characters; no changes committed.', v_student.reg_no;
        END IF;
        v_base_username := left(v_base_username, 150);
        v_candidate := v_base_username;
        v_suffix := 2;

        WHILE EXISTS (
            SELECT 1
              FROM public.accounts_user AS other_user
             WHERE lower(other_user.username) = lower(v_candidate)
               AND other_user.id <> v_student.user_id
        ) LOOP
            v_candidate := left(v_base_username, 150 - length('_' || v_suffix::text))
                           || '_' || v_suffix::text;
            v_suffix := v_suffix + 1;
        END LOOP;

        UPDATE public.accounts_user
           SET username = v_candidate,
               version = COALESCE(version, 1) + 1
         WHERE id = v_student.user_id;
        v_updated := v_updated + 1;
    END LOOP;

    IF v_updated <> 129 THEN
        RAISE EXCEPTION
            'Expected to rename 129 imported student accounts; found %. Transaction rolled back.',
            v_updated;
    END IF;

    RAISE NOTICE 'Renamed % imported student usernames.', v_updated;
END
$rename_student_usernames$;

COMMIT;

-- Verification: expect total_students = 129, unique_usernames = 129,
-- old_roster_usernames_remaining = 0.
SELECT count(*) AS total_students,
       count(DISTINCT lower(u.username)) AS unique_usernames,
       count(*) FILTER (WHERE left(u.username, 7) = 'roster_')
           AS old_roster_usernames_remaining
  FROM public.users_profiles_studentprofile AS p
  JOIN public.accounts_user AS u ON u.id = p.user_id
  JOIN public.accounts_role AS r ON r.id = u.role_id
 WHERE r.code = 'STUDENT'
   AND p.reg_no IN (
        'SEP26-M01', 'SEP26-C02', 'SEP26-C03', 'SEP26-M04', 'SEP26-C05', 'SEP26-E06', 'SEP26-E07', 'SEP26-E08', 'SEP26-C09', 'SEP26-M10', 'SEP26-M11', 'SEP26-M12', 'SEP26-M13', 'SEP26-M14', 'SEP26-M15', 'SEP26-E16', 'SEP26-E17', 'SEP26-C18', 'SEP26-C19', 'SEP26-C20', 'SEP26-C21', 'SEP26-M22', 'SEP26-M23', 'SEP26-M24', 'SEP26-M25', 'SEP26-M26', 'SEP26-M27', 'SEP26-M28', 'SEP26-C29', 'SEP26-E30', 'SEP26-E31', 'SEP26-E32', 'SEP26-E33', 'SEP26-M34', 'SEP26-C35', 'SEP26-E36', 'SEP26-M37', 'SEP26-C38', 'SEP26-C39', 'SEP26-C40', 'SEP26-M41', 'SEP26-M42', 'SEP26-E43', 'SEP26-M44', 'SEP26-E45', 'SEP26-C46', 'SEP26-C47', 'SEP26-C48', 'SEP26-C49', 'SEP26-C50', 'SEP26-E51', 'SEP26-M52', 'SEP26-M53', 'SEP26-C54', 'SEP26-M55', 'SEP26-M56', 'SEP26-M57', 'SEP26-M58', 'SEP26-C59', 'SEP26-C60', 'SEP26-C61', 'SEP26-M62', 'SEP26-M63', 'SEP26-M64', 'OCT26-M01', 'OCT26-M02', 'OCT26-C03', 'OCT26-C04', 'OCT26-C05', 'OCT26-E06', 'OCT26-E07', 'OCT26-E08', 'OCT26-M09', 'OCT26-M10', 'OCT26-M11', 'OCT26-C12', 'OCT26-C13', 'OCT26-C14', 'OCT26-C15', 'OCT26-M16', 'OCT26-E17', 'OCT26-E18', 'OCT26-E19', 'OCT26-M20', 'OCT26-M21', 'OCT26-M22', 'OCT26-M23', 'OCT26-M24', 'OCT26-M25', 'OCT26-M26', 'OCT26-M27', 'OCT26-M28', 'OCT26-E29', 'OCT26-M30', 'OCT26-M31', 'OCT26-M32', 'OCT26-M33', 'OCT26-C34', 'OCT26-C35', 'OCT26-C36', 'OCT26-C37', 'OCT26-C38', 'OCT26-C39', 'OCT26-C40', 'OCT26-C41', 'OCT26-C42', 'OCT26-M43', 'OCT26-C44', 'OCT26-C45', 'OCT26-C46', 'OCT26-C47', 'OCT26-M48', 'OCT26-M49', 'OCT26-C50', 'OCT26-C51', 'OCT26-IT52', 'OCT26-M53', 'OCT26-M54', 'OCT26-E55', 'OCT26-M56', 'OCT26-M57', 'OCT26-M58', 'OCT26-M59', 'OCT26-E60', 'OCT26-M61', 'OCT26-M62', 'OCT26-M63', 'OCT26-E64', 'OCT26-C65'
   );
