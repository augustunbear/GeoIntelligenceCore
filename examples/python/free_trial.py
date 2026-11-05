"""Offline FF-01 composition example. Running this script never sends requests.

Install the providers extra; real Overpass/isochrone calls also need geometry.
For actual calls replace the demonstration in-memory budget with your shared
daily Budget implementation, verify activation gates and explicitly invoke the
returned adapter. ORS_API_KEY is read only at runtime and is never printed.
"""
import os

from geo_intelligence_core.providers.budget import InMemoryBudget
from geo_intelligence_core.providers.trial import TrialSettings, build_trial_provider


def main():
    # For composition only: NOT a daily/persistent/cross-worker quota.
    shared = InMemoryBudget(max_calls=5, cost_ceiling=0)
    print('dry-run: constructs adapters only; sends no HTTP requests')
    for protocol in ('photon', 'overpass', 'ors'):
        settings = TrialSettings.public(protocol, application_name='GeoTrialExample',
                                        contact_url='https://example.org/contact')
        key = os.environ.get('ORS_API_KEY') if protocol == 'ors' else None
        provider = build_trial_provider(settings, budget=shared,
                                        headers={'Authorization': key} if key else None)
        state = 'configured' if provider.gateway.providers[provider.provider_id].endpoint else 'unconfigured'
        print(f'{protocol}: {state}; {settings.instance_id}; {settings.endpoint}; '
              f'{settings.daily_budget_requirement}')


if __name__ == '__main__':
    main()
