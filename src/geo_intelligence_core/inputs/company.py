"""Bounded offline import of explicitly caller-supplied company site records."""
from uuid import uuid4

from ..models.common import Issue, Result, Status
from ..models.company import ImportedCompanySite
from ..models.evidence import Evidence
from ..models.requests import RequestContext

MAX_COMPANY_RECORDS = 1000


def import_company(records: list[dict], evidence: Evidence, *, purpose: str) -> Result[tuple[ImportedCompanySite, ...]]:
    """Validate an atomic batch without fetching, retaining or inferring data.

    Requires source_id/source_ref matching the supplied Evidence and explicit
    site_role. Evidence IDs are attached by this operation, not by input rows.
    Only the exact purpose's use permission is checked; all other rights remain
    separate. Imported assertions do not establish real-world verification.
    """
    context = RequestContext(request_id=str(uuid4()), method_version='company-import-v1',
                             effective_conditions={'purpose': purpose} if isinstance(purpose, str) else {})

    def result(status, data=None, code=None, checked=None):
        return Result[tuple[ImportedCompanySite, ...]](
            status=status, data=data, context=context,
            evidence=(checked,) if checked is not None else (),
            issues=(Issue(code=code, message_key=f'company_import.{code}'),) if code else ())

    try:
        # Roundtrip through JSON revalidates nested model_construct instances,
        # rather than trusting Pydantic's default instance short-circuit.
        if not isinstance(evidence, Evidence):
            raise ValueError('Evidence instance required')
        checked = Evidence.model_validate_json(evidence.model_dump_json(warnings=False))
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        return result(Status.invalid_input, code='invalid_evidence')
    if not isinstance(purpose, str) or not purpose.strip() or not checked.rights.allows('use', purpose):
        return result(Status.disabled, code='use_rights_required', checked=checked)
    if not isinstance(records, list) or len(records) > MAX_COMPANY_RECORDS:
        return result(Status.invalid_input, code='invalid_records', checked=checked)
    try:
        sites = []
        seen = set()
        for row in records:
            if not isinstance(row, dict) or 'evidence_ids' in row:
                raise ValueError('caller dictionaries without evidence_ids required')
            # JSON validation prevents nested unvalidated Pydantic instances.
            site = ImportedCompanySite.model_validate({**row, 'evidence_ids': (checked.id,)})
            site = ImportedCompanySite.model_validate_json(site.model_dump_json(warnings=False))
            if site.source_id != checked.source_id or site.source_ref != checked.source_ref or site.id in seen:
                raise ValueError('ambiguous identity or provenance mismatch')
            seen.add(site.id)
            sites.append(site)
        return result(Status.ok if sites else Status.no_results, tuple(sites), checked=checked)
    except (ValueError, TypeError, AttributeError, OverflowError, RecursionError):
        return result(Status.invalid_input, code='invalid_records', checked=checked)
