"""Company-context template use case (RF-21).

Renders the downloadable `text/plain` template with the guiding sections
(organization profile, strategic alignment, vocabulary and reference
information). The template is a blank document so the administrator fills it
in and re-upload it (upload replaces the current document entirely). It is a
pure read: it never touches the store.
"""

from features.org.domain.company_context import CompanyContext, render_template


def get_context_template() -> str:
    """The plain-text template the administrator downloads (RF-21)."""
    return render_template(CompanyContext.empty(), template=True)
