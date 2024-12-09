import backoff
import httpx
from gql import gql
from gql.client import AsyncClientSession, Client
from gql.transport.exceptions import TransportError, TransportQueryError
from gql.transport.httpx import HTTPXAsyncTransport

from .const import GRAPHQL_CONNECT_RETRIES, GRAPHQL_EXECUTE_RETRIES, HTTPX_TIMEOUT


class _HTTPXAsyncTransport(HTTPXAsyncTransport):
    """GraphQL HTTPXAsyncTransport with pre-existing httpx client"""

    def __init__(self, *args, **kwargs):
        client = kwargs.pop("client")
        super().__init__(*args, **kwargs)
        self.client = client

    async def connect(self):
        pass

    async def close(self):
        pass


def get_gql_client(client: httpx.AsyncClient, url: str) -> Client:
    """Get GraphQL Client using existing httpx AsyncClient"""
    transport = _HTTPXAsyncTransport(url=url, client=client)
    return Client(
        transport=transport,
        fetch_schema_from_transport=False,
        execute_timeout=HTTPX_TIMEOUT,
    )


async def get_gql_session(client: Client) -> AsyncClientSession:
    """Get GraphQL Session with automatic retries"""
    retry_connect = backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(TransportError, httpx.TransportError),
        max_tries=GRAPHQL_CONNECT_RETRIES,
    )
    retry_execute = backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(TransportError,),
        max_tries=GRAPHQL_EXECUTE_RETRIES,
        giveup=lambda e: isinstance(e, TransportQueryError),
    )
    return await client.connect_async(
        reconnecting=True,
        retry_connect=retry_connect,
        retry_execute=retry_execute,
    )


QUERY_GET_CONSUMER_CARS_V2 = gql(
    """
    query GetConsumerCarsV2 {
        getConsumerCarsV2 {
            vin
            internalVehicleIdentifier
            registrationNo
            registrationDate
            factoryCompleteDate
            content {
                model { name }
                images {
                    studio { url }
                }
                specification {
                    battery
                    torque
                }
            }
            software {
                version
                versionTimestamp
            }
        }
    }
    """
)

QUERY_GET_CONSUMER_CARS_V2_VERBOSE = gql(
    """
    query GetConsumerCarsV2 {
        getConsumerCarsV2 {
            vin
            internalVehicleIdentifier
            salesType
            currentPlannedDeliveryDate
            market
            originalMarket
            pno34
            modelYear
            registrationNo
            metaOrderNumber
            factoryCompleteDate
            registrationDate
            deliveryDate
            serviceHistory {
                claimType
                market
                mileage
                mileageUnit
                operations { id code description quantity performedDate }
                orderEndDate
                orderNumber
                orderStartDate
                parts { id code description quantity performedDate }
                statusDMS
                symptomCode
                vehicleAge
                workshopId
            }
            content {
                exterior { code name description excluded }
                exteriorDetails { code name description excluded }
                interior { code name description excluded }
                performancePackage { code name description excluded }
                performanceOptimizationSpecification {
                    power { value unit }
                    torqueMax { value unit }
                    acceleration { value unit description }
                }
                wheels { code name description excluded }
                plusPackage { code name description excluded }
                pilotPackage { code name description excluded }
                motor { name description excluded }
                model { name code }
                images {
                    studio { url angles resolutions }
                    location { url angles resolutions }
                    interior { url angles resolutions }
                }
                specification {
                    battery
                    bodyType
                    brakes
                    combustionEngine
                    electricMotors
                    performance
                    suspension
                    tireSizes
                    torque
                    totalHp
                    totalKw
                    trunkCapacity { label value }
                }
                dimensions {
                    wheelbase { label value }
                    groundClearanceWithPerformance { label value }
                    groundClearanceWithoutPerformance { label value }
                    dimensions { label value }
                }
                towbar { code name description excluded }
            }
            primaryDriver
            primaryDriverRegistrationTimestamp
            owners { id registeredAt information { polestarId ownerType } }
            wltpNedcData {
                wltpCO2Unit
                wltpElecEnergyConsumption
                wltpElecEnergyUnit
                wltpElecRange
                wltpElecRangeUnit
                wltpWeightedCombinedCO2
                wltpWeightedCombinedFuelConsumption
                wltpWeightedCombinedFuelConsumptionUnit
            }
            energy {
                elecRange
                elecRangeUnit
                elecEnergyConsumption
                elecEnergyUnit
                weightedCombinedCO2
                weightedCombinedCO2Unit
                weightedCombinedFuelConsumption
                weightedCombinedFuelConsumptionUnit
            }
            fuelType drivetrain numberOfDoors numberOfSeats
            motor { description code }
            maxTrailerWeight { value unit }
            curbWeight { value unit }
            hasPerformancePackage numberOfCylinders cylinderVolume
            cylinderVolumeUnit transmission numberOfGears structureWeek
            software {
                version
                versionTimestamp
                performanceOptimization { value description timestamp }
            }
            latestClaimStatus { mileage mileageUnit registeredDate vehicleAge }
            internalCar { origin registeredAt }
            edition
            commonStatusPoint { code timestamp description }
            brandStatus { code timestamp description }
            intermediateDestinationCode partnerDestinationCode
            features {
                type
                code
                name
                description
                excluded
                galleryImage { url alt }
                thumbnail { url alt }
            }
            electricalEngineNumbers { number placement }
        }
    }
    """
)

QUERY_GET_ODOMETER_DATA = gql(
    """
    query GetOdometerData($vin:String!) {
        getOdometerData(vin:$vin) {
            averageSpeedKmPerHour
            eventUpdatedTimestamp { iso unix }
            odometerMeters
            tripMeterAutomaticKm
            tripMeterManualKm
        }
    }
    """
)

QUERY_GET_BATTERY_DATA = gql(
    """
    query GetBatteryData($vin:String!) {
        getBatteryData(vin:$vin) {
            averageEnergyConsumptionKwhPer100Km
            batteryChargeLevelPercentage
            chargerConnectionStatus
            chargingCurrentAmps
            chargingPowerWatts
            chargingStatus
            estimatedChargingTimeMinutesToTargetDistance
            estimatedChargingTimeToFullMinutes
            estimatedDistanceToEmptyKm
            estimatedDistanceToEmptyMiles
            eventUpdatedTimestamp { iso unix }
        }
    }
    """
)
