import asyncio
import logging
import sys
import datetime
from ky_client import KYClientManager
from odk_tools.tracking import Tracker
from odk_tools.reporting import report
from momentum_client.manager import MomentumClientManager
from automation_server_client import AutomationServer, Workqueue, WorkItemError, Credential, WorkItemStatus

ky: KYClientManager
momentum: MomentumClientManager
tracker: Tracker
proces_navn = "Visning af borgere uden NemKonto i Momentum - fjern markering"


def populate_queue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Hello from populate workqueue!")

    # Define filters for fetching citizens with tag "Borger har ikke NemKonto"
    filters = [
        {
            "customFilter": "active",
            "fieldName": "tags/id",
            "values": [
                None,
                None,
                None,
                None,
                "bcb40b6b-66c8-457f-814b-2b7138dd0e93"
            ]
        }
    ]
    borgere = momentum.borgere.hent_borgere(filters=filters)
    for borger in borgere['data']:
        workqueue.add_item(
            data={
                "cpr": borger['cpr'],
                "navn": borger['displayName'],
            },
            reference = borger['cpr']
        )


def process_workqueue(workqueue: Workqueue):
    logger = logging.getLogger(__name__)

    logger.info("Hello from process workqueue!")

    for item in workqueue:
        with item:
            data = item.data  # Item data deserialized from json as dict
 
            try:
                borger = ky.borgere.hent_borgersag(data["cpr"])

                ubehandlede_opgaver = borger.get("Ubehandlede opgaver", [])
                nemkonto_opgave = next(
                    (
                        opgave
                        for opgave in ubehandlede_opgaver
                        if "KH - Ingen NemKonto" in opgave.get("Opgave", "")
                    ),
                    None,
                )
                if not nemkonto_opgave:
                    borger = momentum.borgere.hent_borger(data["cpr"])
                    borgers_markeringer = momentum.borgere.hent_markeringer(borger)
                    nemkonto_markering = next((m for m in borgers_markeringer if m['tag']['title'] == "Borger har ikke NemKonto" and m['end'] is None), None)

                    if nemkonto_markering:
                        momentum.borgere.afslut_markering(nemkonto_markering, datetime.datetime.today())
                        tracker.track_task(proces_navn)
                    else:
                        tracker.track_partial_task(proces_navn)


            except WorkItemError as e:
                # A WorkItemError represents a soft error that indicates the item should be passed to manual processing or a business logic fault
                logger.error(f"Error processing item: {data}. Error: {e}")
                item.fail(str(e))


if __name__ == "__main__":
    ats = AutomationServer.from_environment()
    workqueue = ats.workqueue()

    # Initialize external systems for automation here..
    roboa = Credential.get_credential("RoboA")
    tracking_credential = Credential.get_credential("Odense SQL Server")

    tracker = Tracker(
        username=tracking_credential.username, password=tracking_credential.password
    )    

    momentum_credential = Credential.get_credential("Momentum - produktion")
    momentum = MomentumClientManager(
        base_url=momentum_credential.data["base_url"],
        client_id=momentum_credential.username,
        client_secret=momentum_credential.password,
        api_key=momentum_credential.data["api_key"],
        resource=momentum_credential.data["resource"],
        timeout=90.0
    )

    # Queue management
    if "--queue" in sys.argv:
        workqueue.clear_workqueue(WorkItemStatus.NEW)
        populate_queue(workqueue)
        exit(0)

    # Process workqueue
    ky = KYClientManager(
            username=f"{roboa.username}@odense.dk",
            password=roboa.password,
            idp=roboa.data["idp"],
    )
    process_workqueue(workqueue)
