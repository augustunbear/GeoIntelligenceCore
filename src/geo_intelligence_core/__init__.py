"""Public consumer API. Importing the core performs no provider calls."""
from .analysis import analyze, load_profile, load_template
from .comparison import compare
from .evidence import apply_correction, snapshot
from .export import export_result
from .geometry import circle, combine, distance_m
from .location import confirm_location
from .inputs.map_links import parse_map_link
from .inputs.regions import import_region
from .place_quality import (DuplicateCandidate, PlaceQualitySummary, find_duplicate_candidates,
                            normalize_comparison_text, summarize_place_quality)
from .models.analysis import Analysis, Comparison, Correction, Metric, Snapshot
from .models.common import Issue, Result, Status
from .models.configuration import AnalyzeRequest, Profile, Template, TimeCondition, TopicSelection
from .models.evidence import Evidence, Permission, Quality, Rights
from .models.location import Address, Candidate, Confirmation, Entrance, Location, Point
from .models.places import CompanySite, Place, PlaceQuery, PlaceSet, SourceKey
from .models.policy import UsagePolicy
from .models.requests import ConfirmRequest, RequestContext
from .models.spatial import (Catchment, CatchmentRequest, CircleRequest, GeometryLimits,
                             MatrixRequest, Region, Route, RouteRequest, SpatialOperation, TravelMatrix)
from .models.observation import Observation
from .temporal import normalize_observation
from .ports import ProviderRegistry

__version__ = "0.1.0a1"
__all__ = [
    'Address', 'Analysis', 'AnalyzeRequest', 'Candidate', 'Comparison',
    'Catchment', 'CatchmentRequest', 'CircleRequest', 'CompanySite',
    'ConfirmRequest', 'Confirmation', 'Correction', 'Entrance', 'Evidence',
    'GeometryLimits', 'Issue', 'Location', 'MatrixRequest', 'Metric', 'Permission', 'Place', 'PlaceQuery',
    'Observation', 'PlaceSet', 'Point', 'Profile', 'ProviderRegistry', 'Quality', 'Region',
    'RequestContext', 'Result', 'Rights', 'Route', 'RouteRequest', 'Snapshot',
    'SourceKey', 'SpatialOperation', 'Status', 'Template', 'TimeCondition',
    'TopicSelection', 'TravelMatrix', 'UsagePolicy', 'analyze',
    'apply_correction', 'circle', 'combine', 'compare', 'confirm_location',
    'distance_m', 'normalize_observation', 'export_result', 'import_region', 'load_profile', 'load_template',
    'parse_map_link', 'snapshot',
    'DuplicateCandidate', 'PlaceQualitySummary', 'find_duplicate_candidates',
    'normalize_comparison_text', 'summarize_place_quality',
]

