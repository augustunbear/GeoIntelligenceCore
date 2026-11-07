"""Photon API v1 candidate resolver; never confirms a location."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from geo_intelligence_core.models.common import Issue, Result, Status
from geo_intelligence_core.models.location import Address, Candidate, Point
from geo_intelligence_core.models.requests import RequestContext, ReverseRequest, SearchRequest
from geo_intelligence_core.providers.http import HttpGateway
from .context import instance_context


@dataclass(frozen=True)
class PhotonCapabilities:
    """Declared capabilities of the configured Photon API v1 installation.

    Operators must check the installed server version before enabling filters.
    """

    api_version: Literal['v1'] = 'v1'
    supports_countrycode: bool = True
    supports_bbox: bool = True
    supported_languages: tuple[str, ...] = ('de', 'en')
    fallback_language: str = 'de'

    def __post_init__(self):
        if self.api_version != 'v1':
            raise ValueError('unsupported Photon API version')
        if not self.supported_languages or self.fallback_language not in self.supported_languages:
            raise ValueError('fallback_language must be supported')


class PhotonResolver:
    def __init__(self, gateway: HttpGateway, *, provider_id: str = 'photon',
                 capabilities: PhotonCapabilities, min_query_length: int = 2,
                 max_candidates: int = 20):
        if not provider_id or min_query_length < 1 or max_candidates < 1:
            raise ValueError('invalid resolver bounds')
        self.gateway, self.provider_id = gateway, provider_id
        self.capabilities = capabilities
        self.min_query_length, self.max_candidates = min_query_length, max_candidates

    @staticmethod
    def _result(status, context, code=None, data=None, issues=()):
        if code:
            issues = (*issues, Issue(code=code, message_key=f'photon.{code}'))
        return Result[list[Candidate]](status=status, data=data, context=context, issues=issues)

    def _language(self, requested, context):
        effective = (requested if requested in self.capabilities.supported_languages
                     else self.capabilities.fallback_language)
        conditions = dict(context.effective_conditions)
        conditions['language'] = effective
        context = context.model_copy(update={'effective_conditions': conditions})
        issues = () if effective == requested else (
            Issue(code='language_fallback', message_key='photon.language_fallback',
                  safe_params={'requested': requested, 'used': effective}),)
        return effective, context, issues

    async def search(self, request: SearchRequest, context: RequestContext) -> Result[list[Candidate]]:
        try:
            context = RequestContext.model_validate(context)
            context = instance_context(context, self.gateway, self.provider_id)
            request = SearchRequest.model_validate(request)
        except (ValidationError, ValueError, TypeError):
            return self._result(Status.invalid_input, context, 'invalid_request')
        if (len(request.text.strip()) < self.min_query_length or len(request.text) > 256
                or request.limit > self.max_candidates):
            return self._result(Status.invalid_input, context, 'query_bounds')
        countries = tuple(code.upper() for code in request.country_codes)
        if any(len(code) != 2 or not code.isascii() or not code.isalpha() for code in countries):
            return self._result(Status.invalid_input, context, 'country_code')
        if len(countries) > 1 or (countries and not self.capabilities.supports_countrycode):
            return self._result(Status.unsupported, context, 'country_filter')
        bbox = request.bbox
        if bbox and (not self.capabilities.supports_bbox):
            return self._result(Status.unsupported, context, 'bbox_filter')
        if bbox and not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
            return self._result(Status.invalid_input, context, 'bbox')
        language, context, issues = self._language(request.language, context)
        params = {'q': request.text.strip(), 'lang': language, 'limit': request.limit}
        if countries:
            params['countrycode'] = countries[0]
        if bbox:
            params['bbox'] = ','.join(map(str, bbox))
        if request.near:
            params.update(lon=request.near.longitude, lat=request.near.latitude)
        return await self._query('/api', params, context, issues, request.limit, countries, bbox, language)

    async def reverse(self, request: ReverseRequest, context: RequestContext) -> Result[list[Candidate]]:
        try:
            context = RequestContext.model_validate(context)
            context = instance_context(context, self.gateway, self.provider_id)
            request = ReverseRequest.model_validate(request)
        except (ValidationError, ValueError, TypeError):
            return self._result(Status.invalid_input, context, 'invalid_request')
        language, context, issues = self._language(request.language, context)
        return await self._query('/reverse', {'lon': request.point.longitude,
                                              'lat': request.point.latitude, 'lang': language,
                                              'limit': self.max_candidates}, context, issues,
                                 self.max_candidates, (), None, language)

    async def _query(self, path, params, context, issues, limit, countries, bbox, language):
        context = instance_context(context, self.gateway, self.provider_id)
        # Cancellation propagates through the gateway and stops subsequent retry attempts.
        response = await self.gateway.request(self.provider_id, 'GET', path, params, context)
        if response.status != Status.ok:
            return Result[list[Candidate]](status=response.status, data=None,
                                           context=context, issues=(*issues, *response.issues))
        try:
            features = response.data['features']
            if not isinstance(features, (list, tuple)) or len(features) > limit:
                raise ValueError('invalid feature list')
            candidates = [self._candidate(feature, language) for feature in features]
            # One OSM object is one candidate identity. Repeated features may
            # disagree on name or point, so selecting one would hide bad source
            # evidence and could make a measured quality gate pass incorrectly.
            if len({candidate.id for candidate in candidates}) != len(candidates):
                raise ValueError('duplicate OSM candidate identity')
            candidates = [candidate for candidate in candidates
                          if (not countries or candidate.address.country_code in countries)
                          and (not bbox or bbox[0] <= candidate.point.longitude <= bbox[2]
                               and bbox[1] <= candidate.point.latitude <= bbox[3])]
        except (KeyError, TypeError, ValueError, ValidationError):
            return self._result(Status.unavailable, context, 'invalid_response', issues=issues)
        return self._result(Status.ok if candidates else Status.no_results, context,
                            data=candidates, issues=issues)

    @staticmethod
    def _candidate(feature, language):
        if feature['type'] != 'Feature' or feature['geometry']['type'] != 'Point':
            raise ValueError('unsupported geometry')
        coordinates = feature['geometry']['coordinates']
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
            raise ValueError('invalid coordinates')
        point = Point(longitude=coordinates[0], latitude=coordinates[1])
        props = feature['properties']
        osm_type, osm_id = props['osm_type'], props['osm_id']
        if osm_type not in ('N', 'W', 'R') or type(osm_id) is not int or osm_id < 1:
            raise ValueError('missing OSM identity')
        name = props.get('name')
        if name is not None and (not isinstance(name, str) or not name):
            raise ValueError('invalid name')
        extra = props.get('extra') or {}
        if not isinstance(extra, dict):
            raise ValueError('invalid extra')
        names = {language: name} if name else {}
        original = extra.get('name')
        if isinstance(original, str) and original:
            names['und'] = original
        keys = {'country_code': 'countrycode', 'postcode': 'postcode',
                'locality': 'city', 'street': 'street', 'house_number': 'housenumber'}
        address = {target: props.get(source) for target, source in keys.items()}
        if any(value is not None and not isinstance(value, str) for value in address.values()):
            raise ValueError('invalid address')
        if address['country_code']:
            address['country_code'] = address['country_code'].upper()
        address['native_names'] = names
        precision = ('house' if address['street'] and address['house_number'] else
                     'street' if address['street'] else
                     'locality' if address['locality'] else 'unknown')
        source = f'photon:osm:{osm_type}:{osm_id}'
        return Candidate(id=source, source_ref=source, point=point,
                         address=Address(**address), precision=precision)
