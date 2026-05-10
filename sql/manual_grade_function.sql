create or replace function log_manual_grade(
    p_student_id uuid,
    p_activity_id uuid,
    p_instructor_id uuid,
    p_score integer,
    p_reason text
)
returns void
language plpgsql
as $$
begin
    insert into score_logs (
        student_id,
        activity_id,
        score_delta,
        reason,
        created_by
    )
    values (
        p_student_id,
        p_activity_id,
        p_score,
        p_reason,
        p_instructor_id
    );
end;
$$;
