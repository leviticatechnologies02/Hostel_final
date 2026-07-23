"""
Premium HTML email templates for contact form emails.
Two templates:
  1. contact_lead_html_v2      — Customer confirmation
  2. owner_notification_html_v2 — Owner internal CRM alert
"""


def contact_lead_html_v2(
    full_name: str,
    hostel_name: str,
    city: str,
    inquiry_type: str,
    message: str,
) -> str:
    """Premium confirmation email sent to the hostel owner who submitted the form."""
    return (
        "<!DOCTYPE html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"/>'
        "<title>We received your inquiry</title>"
        "</head>"
        '<body style="margin:0;padding:0;background-color:#f3f4f6;'
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;\">"
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background-color:#f3f4f6;padding:40px 0;">'
        "<tr><td align=\"center\">"
        '<table width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:600px;width:100%;">'
        # LOGO
        "<tr><td align=\"center\" style=\"padding:0 0 24px 0;\">"
        '<table cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="background-color:#0F766E;border-radius:12px;padding:10px 18px;">'
        '<span style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">Hostel</span>'
        '<span style="font-size:22px;font-weight:800;color:#99f6e4;letter-spacing:-0.5px;">Hub</span>'
        '</td><td style="padding-left:12px;">'
        '<span style="font-size:12px;color:#6b7280;font-weight:500;">by Levitica Technologies</span>'
        '</td></tr></table></td></tr>'
        # MAIN CARD
        '<tr><td style="background-color:#ffffff;border-radius:16px;overflow:hidden;'
        'box-shadow:0 4px 24px rgba(0,0,0,0.08);">'
        # TEAL HEADER
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="background:linear-gradient(135deg,#0F766E 0%,#0d9488 100%);'
        'padding:40px 40px 36px;text-align:center;">'
        '<div style="width:60px;height:60px;background:rgba(255,255,255,0.15);border-radius:50%;'
        'margin:0 auto 16px;font-size:28px;line-height:60px;text-align:center;">&#10003;</div>'
        '<h1 style="margin:0;font-size:26px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">'
        'Inquiry Received!</h1>'
        '<p style="margin:10px 0 0;font-size:15px;color:rgba(255,255,255,0.85);">'
        'We&rsquo;ll get back to you within 24 hours</p>'
        '</td></tr></table>'
        # BODY
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="padding:36px 40px;">'
        f'<p style="margin:0 0 8px;font-size:16px;color:#374151;">Dear '
        f'<strong style="color:#111827;">{full_name}</strong>,</p>'
        '<p style="margin:0 0 28px;font-size:15px;color:#6b7280;line-height:1.6;">'
        'Thank you for reaching out to HostelHub. We have successfully received your inquiry '
        'and our team is already reviewing it. Expect to hear from us within '
        '<strong style="color:#0F766E;">24 hours</strong>.</p>'
        # SUMMARY CARD
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background:#f9fafb;border-radius:12px;border:1px solid #e5e7eb;margin-bottom:28px;">'
        '<tr><td style="padding:20px 24px 8px;">'
        '<p style="margin:0;font-size:11px;font-weight:700;color:#0F766E;'
        'letter-spacing:1.2px;text-transform:uppercase;">&#128203; Your Inquiry Summary</p>'
        '</td></tr>'
        '<tr><td style="padding:0 24px;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr>'
        '<td style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:13px;color:#6b7280;width:42%;">'
        '&#127970; Hostel / Organization</td>'
        f'<td style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:13px;'
        f'color:#111827;font-weight:600;">{hostel_name}</td>'
        '</tr><tr>'
        '<td style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:13px;color:#6b7280;">'
        '&#128205; City</td>'
        f'<td style="padding:10px 0;border-bottom:1px solid #e5e7eb;font-size:13px;'
        f'color:#111827;font-weight:600;">{city}</td>'
        '</tr><tr>'
        '<td style="padding:10px 0;font-size:13px;color:#6b7280;">&#127981; Inquiry Type</td>'
        f'<td style="padding:10px 0;font-size:13px;color:#111827;font-weight:600;">{inquiry_type}</td>'
        '</tr></table></td></tr>'
        '<tr><td style="padding:12px 24px 20px;">'
        '<p style="margin:0 0 8px;font-size:13px;color:#6b7280;">&#128172; Your Message</p>'
        f'<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;padding:14px;'
        f'font-size:14px;color:#4b5563;line-height:1.6;font-style:italic;">{message}</div>'
        '</td></tr></table>'
        # NEXT STEPS
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background:linear-gradient(135deg,#f0fdfa,#ecfdf5);border-radius:12px;'
        'border:1px solid #a7f3d0;margin-bottom:28px;">'
        '<tr><td style="padding:20px 24px;">'
        '<p style="margin:0 0 14px;font-size:11px;font-weight:700;color:#065f46;'
        'letter-spacing:1.2px;text-transform:uppercase;">&#128640; What Happens Next?</p>'
        '<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        '<tr><td style="padding:5px 0;font-size:14px;color:#065f46;">'
        '<span style="margin-right:8px;">&#9312;</span>Our team reviews your inquiry</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#065f46;">'
        '<span style="margin-right:8px;">&#9313;</span>We contact you within 24 hours</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#065f46;">'
        '<span style="margin-right:8px;">&#9314;</span>Personalized demo scheduled for you</td></tr>'
        '</table></td></tr></table>'
        # CONTACT
        '<p style="margin:0 0 6px;font-size:14px;color:#374151;">If urgent, reach us directly:</p>'
        '<p style="margin:0 0 28px;font-size:14px;color:#6b7280;line-height:1.8;">'
        '&#128222;&nbsp;<a href="tel:+919032503559" style="color:#0F766E;text-decoration:none;'
        'font-weight:600;">+91 9032503559</a><br>'
        '&#128231;&nbsp;<a href="mailto:hr@leviticatechnologies.com" '
        'style="color:#0F766E;text-decoration:none;font-weight:600;">hr@leviticatechnologies.com</a>'
        '</p>'
        '<p style="margin:0;font-size:14px;color:#374151;line-height:1.6;">Thank you for choosing '
        '<strong style="color:#0F766E;">HostelHub</strong>. We look forward to helping you '
        'streamline your hostel operations.</p>'
        '<p style="margin:20px 0 0;font-size:14px;color:#374151;">Warm regards,<br>'
        '<strong style="color:#111827;">The Levitica Nestora Team</strong><br>'
        '<span style="font-size:12px;color:#9ca3af;">Levitica Technologies Pvt. Ltd.</span></p>'
        '</td></tr></table>'
        '</td></tr>'
        # FOOTER
        '<tr><td style="padding:24px 0;text-align:center;">'
        '<p style="margin:0 0 8px;font-size:12px;color:#9ca3af;">'
        '<a href="https://hostelhub.in" style="color:#0F766E;text-decoration:none;">HostelHub</a>'
        ' &middot; '
        '<a href="https://leviticatechnologies.com" style="color:#0F766E;text-decoration:none;">'
        'Levitica Technologies</a>'
        ' &middot; '
        '<a href="mailto:hr@leviticatechnologies.com" style="color:#0F766E;text-decoration:none;">'
        'Contact Support</a></p>'
        '<p style="margin:0;font-size:11px;color:#d1d5db;">'
        '&copy; 2026 Levitica Technologies Pvt. Ltd. All rights reserved.</p>'
        '</td></tr>'
        '</table></td></tr></table>'
        '</body></html>'
    )


def owner_notification_html_v2(
    first_name: str,
    last_name: str,
    organization_name: str,
    email: str,
    phone: str,
    message: str,
    submitted_at: str,
) -> str:
    """Premium internal CRM notification email sent to software owner on new lead."""
    return (
        "<!DOCTYPE html>"
        '<html lang="en">'
        "<head>"
        '<meta charset="UTF-8"/>'
        '<meta name="viewport" content="width=device-width,initial-scale=1"/>'
        "<title>New Lead | HostelHub</title>"
        "</head>"
        '<body style="margin:0;padding:0;background-color:#f3f4f6;'
        "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;\">"
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="background-color:#f3f4f6;padding:40px 0;">'
        "<tr><td align=\"center\">"
        '<table width="600" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:600px;width:100%;">'
        # LOGO
        '<tr><td align="center" style="padding:0 0 24px 0;">'
        '<table cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="background-color:#0F766E;border-radius:12px;padding:10px 18px;">'
        '<span style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">Hostel</span>'
        '<span style="font-size:22px;font-weight:800;color:#99f6e4;letter-spacing:-0.5px;">Hub</span>'
        '</td><td style="padding-left:12px;">'
        '<span style="font-size:12px;color:#6b7280;font-weight:500;">Internal CRM Notification</span>'
        '</td></tr></table></td></tr>'
        # URGENT BANNER
        '<tr><td style="background:linear-gradient(135deg,#dc2626,#b91c1c);border-radius:10px;'
        'padding:14px 24px;text-align:center;">'
        '<p style="margin:0;font-size:13px;font-weight:700;color:#ffffff;letter-spacing:0.5px;">'
        '&#9888;&nbsp; ACTION REQUIRED &mdash; Respond within 24 hours &nbsp;&#9888;</p>'
        '</td></tr>'
        '<tr><td style="height:16px;"></td></tr>'
        # MAIN CARD
        '<tr><td style="background-color:#ffffff;border-radius:16px;overflow:hidden;'
        'box-shadow:0 4px 24px rgba(0,0,0,0.08);">'
        # TEAL HEADER
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="background:linear-gradient(135deg,#0F766E,#0d9488);padding:36px 40px;">'
        '<p style="margin:0 0 4px;font-size:12px;font-weight:600;color:rgba(255,255,255,0.7);'
        'letter-spacing:1.5px;text-transform:uppercase;">New Inquiry</p>'
        f'<h1 style="margin:0 0 6px;font-size:24px;font-weight:700;color:#ffffff;">'
        f'&#128236; {organization_name}</h1>'
        f'<p style="margin:0;font-size:14px;color:rgba(255,255,255,0.8);">'
        f'{first_name} {last_name} &bull; {submitted_at}</p>'
        '</td></tr></table>'
        # BODY
        '<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>'
        '<td style="padding:32px 40px;">'
        '<p style="margin:0 0 24px;font-size:15px;color:#374151;line-height:1.6;">'
        'Hello Team, a new inquiry has been submitted through the '
        '<strong style="color:#0F766E;">HostelHub Contact Form</strong>. '
        'Please review the details below and take the required action.</p>'
        # CUSTOMER CARD
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">'
        '<tr><td style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:12px;padding:20px 24px;">'
        '<p style="margin:0 0 16px;font-size:11px;font-weight:700;color:#0F766E;'
        'letter-spacing:1.5px;text-transform:uppercase;">&#128100; Customer Details</p>'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr>'
        '<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;color:#6b7280;width:40%;">'
        'Full Name</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;'
        f'font-weight:700;color:#0f172a;">{first_name} {last_name}</td>'
        '</tr><tr>'
        '<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;color:#6b7280;">'
        'Organization</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;'
        f'font-weight:700;color:#0f172a;">{organization_name}</td>'
        '</tr><tr>'
        '<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;color:#6b7280;">'
        'Email</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #ccfbf1;font-size:13px;font-weight:600;">'
        f'<a href="mailto:{email}" style="color:#0F766E;text-decoration:none;">{email}</a></td>'
        '</tr><tr>'
        '<td style="padding:8px 0;font-size:13px;color:#6b7280;">Phone</td>'
        f'<td style="padding:8px 0;font-size:13px;font-weight:700;color:#0f172a;">'
        f'<a href="tel:{phone}" style="color:#0F766E;text-decoration:none;">{phone}</a></td>'
        '</tr></table></td></tr></table>'
        # MESSAGE CARD
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">'
        '<tr><td style="background:#fafafa;border:1px solid #e5e7eb;border-radius:12px;padding:20px 24px;">'
        '<p style="margin:0 0 12px;font-size:11px;font-weight:700;color:#374151;'
        'letter-spacing:1.5px;text-transform:uppercase;">&#128172; Customer Message</p>'
        f'<p style="margin:0;font-size:14px;color:#4b5563;line-height:1.7;white-space:pre-wrap;">{message}</p>'
        '</td></tr></table>'
        # SUBMISSION DETAILS
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:24px;">'
        '<tr><td style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;">'
        '<p style="margin:0 0 12px;font-size:11px;font-weight:700;color:#64748b;'
        'letter-spacing:1.5px;text-transform:uppercase;">&#128203; Submission Details</p>'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr>'
        '<td style="padding:6px 0;font-size:13px;color:#6b7280;width:40%;">&#128197; Submitted On</td>'
        f'<td style="padding:6px 0;font-size:13px;color:#374151;font-weight:600;">{submitted_at}</td>'
        '</tr><tr>'
        '<td style="padding:6px 0;font-size:13px;color:#6b7280;">&#127760; Source</td>'
        '<td style="padding:6px 0;font-size:13px;color:#374151;font-weight:600;">'
        'Levitica Nestora Website &mdash; Contact Form</td>'
        '</tr><tr>'
        '<td style="padding:6px 0;font-size:13px;color:#6b7280;">&#128279; Page</td>'
        '<td style="padding:6px 0;font-size:13px;color:#374151;font-weight:600;">Contact Us</td>'
        '</tr></table></td></tr></table>'
        # NEXT STEPS
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:28px;">'
        '<tr><td style="background:linear-gradient(135deg,#ecfdf5,#f0fdf4);border:1px solid #bbf7d0;'
        'border-radius:12px;padding:20px 24px;">'
        '<p style="margin:0 0 14px;font-size:11px;font-weight:700;color:#15803d;'
        'letter-spacing:1.5px;text-transform:uppercase;">&#9989; Next Steps &mdash; Action Required</p>'
        '<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        '<tr><td style="padding:5px 0;font-size:14px;color:#166534;">'
        '<span style="font-weight:700;margin-right:8px;">1.</span>'
        'Contact the customer within 24 hours</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#166534;">'
        '<span style="font-weight:700;margin-right:8px;">2.</span>'
        'Understand their hostel management requirements</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#166534;">'
        '<span style="font-weight:700;margin-right:8px;">3.</span>'
        'Schedule a personalized product demonstration</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#166534;">'
        '<span style="font-weight:700;margin-right:8px;">4.</span>'
        'Explain features, pricing &amp; onboarding process</td></tr>'
        '<tr><td style="padding:5px 0;font-size:14px;color:#166534;">'
        '<span style="font-weight:700;margin-right:8px;">5.</span>'
        'Answer all questions and update the inquiry status</td></tr>'
        '</table></td></tr></table>'
        '<p style="margin:0;font-size:12px;color:#9ca3af;border-top:1px solid #f3f4f6;'
        'padding-top:20px;text-align:center;">'
        'This is an automated notification from the HostelHub Contact Portal.<br>'
        '<strong style="color:#374151;">HostelHub &mdash; Levitica Technologies Pvt. Ltd.</strong>'
        '</p></td></tr></table></td></tr>'
        # FOOTER
        '<tr><td style="padding:24px 0;text-align:center;">'
        '<p style="margin:0 0 8px;font-size:12px;color:#9ca3af;">'
        '<a href="https://hostelhub.in" style="color:#0F766E;text-decoration:none;">HostelHub</a>'
        ' &middot; '
        '<a href="https://leviticatechnologies.com" style="color:#0F766E;text-decoration:none;">'
        'Levitica Technologies</a>'
        ' &middot; '
        '<a href="mailto:hr@leviticatechnologies.com" style="color:#0F766E;text-decoration:none;">'
        'hr@leviticatechnologies.com</a></p>'
        '<p style="margin:0;font-size:11px;color:#d1d5db;">'
        '&copy; 2026 Levitica Technologies Pvt. Ltd. All rights reserved.</p>'
        '</td></tr>'
        '</table></td></tr></table>'
        '</body></html>'
    )
