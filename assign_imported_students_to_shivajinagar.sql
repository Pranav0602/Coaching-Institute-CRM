-- Assign the imported student roster to the existing SHIVAJI NAGAR branch (code 01).
-- Run this in pgAdmin Query Tool while connected to the Render/server database.
-- The branch UUID is looked up on that database; no local UUID is assumed.
-- Only the 129 registration numbers from STUDENT_DATA_CRM are targeted.

BEGIN;

DO $assign_shivajinagar$
DECLARE
    v_branch_id uuid;
    v_updated integer;
BEGIN
    SELECT b.id
      INTO STRICT v_branch_id
      FROM public.accounts_branch AS b
     WHERE b.code = '01'
       AND b.is_deleted = false;

    UPDATE public.accounts_user AS u
       SET branch_id = v_branch_id,
           version = COALESCE(u.version, 1) + 1
      FROM public.users_profiles_studentprofile AS p,
           (VALUES
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
           ) AS roster(reg_no),
           public.accounts_role AS r
     WHERE u.id = p.user_id
       AND p.reg_no = roster.reg_no
       AND r.id = u.role_id
       AND r.code = 'STUDENT'
       AND u.is_deleted = false
       AND p.is_deleted = false;

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    IF v_updated <> 129 THEN
        RAISE EXCEPTION
            'Expected to assign 129 imported students; updated %. Transaction rolled back.',
            v_updated;
    END IF;

    RAISE NOTICE 'Assigned % imported students to SHIVAJI NAGAR (branch code 01).', v_updated;
END
$assign_shivajinagar$;

COMMIT;

-- Verification: this should return 129.
SELECT count(*) AS imported_students_assigned_to_shivajinagar
  FROM public.users_profiles_studentprofile AS p
  JOIN public.accounts_user AS u ON u.id = p.user_id
  JOIN public.accounts_role AS r ON r.id = u.role_id
  JOIN public.accounts_branch AS b ON b.id = u.branch_id
 WHERE b.code = '01'
   AND r.code = 'STUDENT'
   AND p.reg_no IN (
        'SEP26-M01', 'SEP26-C02', 'SEP26-C03', 'SEP26-M04', 'SEP26-C05', 'SEP26-E06', 'SEP26-E07', 'SEP26-E08', 'SEP26-C09', 'SEP26-M10', 'SEP26-M11', 'SEP26-M12', 'SEP26-M13', 'SEP26-M14', 'SEP26-M15', 'SEP26-E16', 'SEP26-E17', 'SEP26-C18', 'SEP26-C19', 'SEP26-C20', 'SEP26-C21', 'SEP26-M22', 'SEP26-M23', 'SEP26-M24', 'SEP26-M25', 'SEP26-M26', 'SEP26-M27', 'SEP26-M28', 'SEP26-C29', 'SEP26-E30', 'SEP26-E31', 'SEP26-E32', 'SEP26-E33', 'SEP26-M34', 'SEP26-C35', 'SEP26-E36', 'SEP26-M37', 'SEP26-C38', 'SEP26-C39', 'SEP26-C40', 'SEP26-M41', 'SEP26-M42', 'SEP26-E43', 'SEP26-M44', 'SEP26-E45', 'SEP26-C46', 'SEP26-C47', 'SEP26-C48', 'SEP26-C49', 'SEP26-C50', 'SEP26-E51', 'SEP26-M52', 'SEP26-M53', 'SEP26-C54', 'SEP26-M55', 'SEP26-M56', 'SEP26-M57', 'SEP26-M58', 'SEP26-C59', 'SEP26-C60', 'SEP26-C61', 'SEP26-M62', 'SEP26-M63', 'SEP26-M64', 'OCT26-M01', 'OCT26-M02', 'OCT26-C03', 'OCT26-C04', 'OCT26-C05', 'OCT26-E06', 'OCT26-E07', 'OCT26-E08', 'OCT26-M09', 'OCT26-M10', 'OCT26-M11', 'OCT26-C12', 'OCT26-C13', 'OCT26-C14', 'OCT26-C15', 'OCT26-M16', 'OCT26-E17', 'OCT26-E18', 'OCT26-E19', 'OCT26-M20', 'OCT26-M21', 'OCT26-M22', 'OCT26-M23', 'OCT26-M24', 'OCT26-M25', 'OCT26-M26', 'OCT26-M27', 'OCT26-M28', 'OCT26-E29', 'OCT26-M30', 'OCT26-M31', 'OCT26-M32', 'OCT26-M33', 'OCT26-C34', 'OCT26-C35', 'OCT26-C36', 'OCT26-C37', 'OCT26-C38', 'OCT26-C39', 'OCT26-C40', 'OCT26-C41', 'OCT26-C42', 'OCT26-M43', 'OCT26-C44', 'OCT26-C45', 'OCT26-C46', 'OCT26-C47', 'OCT26-M48', 'OCT26-M49', 'OCT26-C50', 'OCT26-C51', 'OCT26-IT52', 'OCT26-M53', 'OCT26-M54', 'OCT26-E55', 'OCT26-M56', 'OCT26-M57', 'OCT26-M58', 'OCT26-M59', 'OCT26-E60', 'OCT26-M61', 'OCT26-M62', 'OCT26-M63', 'OCT26-E64', 'OCT26-C65'
   );
