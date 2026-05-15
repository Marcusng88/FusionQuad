import asyncio

from app.services.simulation import SimulationService


def test_play_advances_intervals_until_paused():
    async def scenario() -> None:
        service = SimulationService()
        snapshot = await service.start(day_type="weekday", bess_capacity_kwh=500.0)
        session_id = snapshot.session_id

        started = await service.play(session_id, interval_seconds=0.001)
        assert started.status == "playing"

        await asyncio.sleep(0.03)
        progressed = await service.get_state(session_id)
        assert progressed.current_interval >= 1

        paused = await service.pause(session_id)
        interval_after_pause = paused.current_interval

        await asyncio.sleep(0.02)
        after = await service.get_state(session_id)
        assert after.status == "paused"
        assert after.current_interval == interval_after_pause

    asyncio.run(scenario())
