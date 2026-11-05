from geo_intelligence_core.configuration import resolve_config
from geo_intelligence_core.models.common import Status
from geo_intelligence_core.models.configuration import AnalyzeRequest, Profile, Template, TopicSelection
from geo_intelligence_core.models.location import Location
from geo_intelligence_core.models.policy import UsagePolicy
from geo_intelligence_core.ports import ProviderRegistry


def request(**kwargs):
    return AnalyzeRequest(locations=[], topics=[TopicSelection(id='places')], **kwargs)


def test_precedence_and_policy_hard_ceiling():
    profile = Profile(id='food', version='1', defaults={'radius_m': 200, 'language': 'de'})
    template = Template(id='nearby', version='1', profile_ref='food@1', defaults={'radius_m': 1000})
    policy = UsagePolicy(allowed_capabilities=['places'], max_area_m2=3.141592653589793*800**2)
    registry = ProviderRegistry()
    registry.register('places', object())
    ok = resolve_config(request(explicit_parameters={'radius_m': 500}), profile, template, policy, registry=registry)
    assert ok.status == Status.ok
    assert ok.data.values['radius_m'] == 500
    assert ok.data.provenance_by_field['radius_m'] == 'request'
    assert ok.data.provenance_by_field['language'] == 'profile'
    invalid = resolve_config(request(explicit_parameters={'radius_m': 900}), profile, template, policy, registry=registry)
    assert invalid.status == Status.invalid_input and invalid.data is None


def test_missing_required_capability_never_calls_provider():
    class Fake:
        calls = 0
    fake = Fake()
    registry = ProviderRegistry()
    registry.register('places', fake, configured=False)
    template = Template(id='t', version='1', required_topics=['places'])
    policy = UsagePolicy(allowed_capabilities=['places'])
    result = resolve_config(AnalyzeRequest(locations=[], topics=[TopicSelection(id='places', required=False)]),
                            None, template, policy, registry=registry)
    assert result.status == Status.unconfigured and fake.calls == 0
    assert result.context.effective_conditions['required_topics'] == 'places'


def test_population_selection_and_required_union():
    policy = UsagePolicy(allowed_capabilities=['places'])
    registry = ProviderRegistry()
    registry.register('places', object())
    assert resolve_config(request(), None, None, policy, registry=registry).status == Status.ok
    selected = AnalyzeRequest(locations=[], topics=[TopicSelection(id='places'), TopicSelection(id='population')])
    result = resolve_config(selected, None, None, policy, registry=registry)
    assert result.status == Status.partial
    assert any(i.code == 'capability_disabled' for i in result.issues)
    assert resolve_config(AnalyzeRequest(locations=[], topics=[TopicSelection(id='population', required=True)]), None, None, policy).status == Status.disabled


def test_invalid_requests_and_languages():
    policy = UsagePolicy(allowed_capabilities=['places'])
    for params in ({'surprise': 1}, {'language': 'fr'}, {'radius_m': '500'}):
        assert resolve_config(request(explicit_parameters=params), None, None, policy).status == Status.invalid_input
    duplicate = AnalyzeRequest(locations=[], topics=[TopicSelection(id='places'), TopicSelection(id='places')])
    assert resolve_config(duplicate, None, None, policy).status == Status.invalid_input
    template = Template(id='t', version='1', required_topics=['places'])
    assert resolve_config(AnalyzeRequest(locations=[], topics=[]), None, template, policy).status == Status.invalid_input
