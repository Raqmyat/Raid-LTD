def post_init_hook(env):
    """Align already existing time off requests with the new cycle status:
    validated -> done, refused -> refused, cancelled -> cancelled, the rest stays pending."""
    env.cr.execute("""
        UPDATE hr_leave
           SET leave_appr_state = CASE state
                 WHEN 'validate' THEN 'done'
                 WHEN 'refuse' THEN 'refused'
                 WHEN 'cancel' THEN 'cancelled'
                 ELSE leave_appr_state END
         WHERE state IN ('validate', 'refuse', 'cancel')
    """)
