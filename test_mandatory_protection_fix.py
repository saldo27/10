#!/usr/bin/env python3
"""
Test script to verify that mandatory shifts are properly protected
during the initial distribution phase.
"""

import logging
import sys
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_mandatory_protection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def test_mandatory_protection():
    """
    Test that mandatory shifts are protected during initial distribution.
    """
    logging.info("=" * 80)
    logging.info("TESTING MANDATORY SHIFT PROTECTION")
    logging.info("=" * 80)
    
    try:
        from scheduler import Scheduler
        from scheduler_config import SchedulerConfig
        
        # Create a simple test configuration
        config = SchedulerConfig()
        
        # Define test period (one month)
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 31)
        
        # Create test workers with mandatory days
        workers_data = [
            {
                'id': 'W1',
                'target_shifts': 15,
                'work_percentage': 100,
                'mandatory_days': '05-01-2025;15-01-2025;25-01-2025',  # 3 mandatory days
                'days_off': '',
                'work_periods': '',
                'incompatible_with': []
            },
            {
                'id': 'W2',
                'target_shifts': 15,
                'work_percentage': 100,
                'mandatory_days': '10-01-2025;20-01-2025',  # 2 mandatory days
                'days_off': '',
                'work_periods': '',
                'incompatible_with': []
            },
            {
                'id': 'W3',
                'target_shifts': 15,
                'work_percentage': 100,
                'mandatory_days': '',  # No mandatory days
                'days_off': '',
                'work_periods': '',
                'incompatible_with': []
            },
        ]
        
        logging.info(f"Test configuration:")
        logging.info(f"  Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logging.info(f"  Workers: {len(workers_data)}")
        logging.info(f"  W1 mandatory: 05-01, 15-01, 25-01")
        logging.info(f"  W2 mandatory: 10-01, 20-01")
        logging.info(f"  W3 mandatory: none")
        
        # Create scheduler
        scheduler = Scheduler(
            start_date=start_date,
            end_date=end_date,
            workers_data=workers_data,
            num_shifts=2,
            holidays=[],
            config=config
        )
        
        logging.info("\n" + "=" * 80)
        logging.info("PHASE 1: Generate Schedule")
        logging.info("=" * 80)
        
        # Generate schedule
        success = scheduler.generate_schedule()
        
        if not success:
            logging.error("❌ Schedule generation FAILED")
            return False
        
        logging.info("✅ Schedule generation completed")
        
        # Verify mandatory shifts
        logging.info("\n" + "=" * 80)
        logging.info("PHASE 2: Verify Mandatory Shifts Protection")
        logging.info("=" * 80)
        
        mandatory_dates_w1 = [
            datetime(2025, 1, 5),
            datetime(2025, 1, 15),
            datetime(2025, 1, 25)
        ]
        
        mandatory_dates_w2 = [
            datetime(2025, 1, 10),
            datetime(2025, 1, 20)
        ]
        
        errors = 0
        
        # Check W1 mandatory dates
        for date in mandatory_dates_w1:
            if date in scheduler.schedule:
                if 'W1' in scheduler.schedule[date]:
                    logging.info(f"✅ W1 correctly assigned on {date.strftime('%Y-%m-%d')} (mandatory)")
                else:
                    logging.error(f"❌ W1 NOT found on {date.strftime('%Y-%m-%d')} (mandatory) - VIOLATION!")
                    errors += 1
            else:
                logging.error(f"❌ Date {date.strftime('%Y-%m-%d')} not in schedule - ERROR")
                errors += 1
        
        # Check W2 mandatory dates
        for date in mandatory_dates_w2:
            if date in scheduler.schedule:
                if 'W2' in scheduler.schedule[date]:
                    logging.info(f"✅ W2 correctly assigned on {date.strftime('%Y-%m-%d')} (mandatory)")
                else:
                    logging.error(f"❌ W2 NOT found on {date.strftime('%Y-%m-%d')} (mandatory) - VIOLATION!")
                    errors += 1
            else:
                logging.error(f"❌ Date {date.strftime('%Y-%m-%d')} not in schedule - ERROR")
                errors += 1
        
        # Summary
        logging.info("\n" + "=" * 80)
        logging.info("TEST SUMMARY")
        logging.info("=" * 80)
        
        if errors == 0:
            logging.info("✅ ALL MANDATORY SHIFTS PROTECTED CORRECTLY")
            logging.info("✅ TEST PASSED")
            return True
        else:
            logging.error(f"❌ {errors} MANDATORY SHIFT VIOLATIONS DETECTED")
            logging.error("❌ TEST FAILED")
            return False
            
    except Exception as e:
        logging.error(f"❌ Test failed with exception: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_mandatory_protection()
    sys.exit(0 if success else 1)
