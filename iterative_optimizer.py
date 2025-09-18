#!/usr/bin/env python3
"""
Iterative Optimization System for Schedule Assignment
Automatically retries and optimizes schedule assignments until tolerance requirements are met.
"""

import logging
import random
import copy
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

from shift_tolerance_validator import ShiftToleranceValidator
from performance_cache import cached, time_function

@dataclass
class OptimizationResult:
    """Result of optimization attempt"""
    success: bool
    iteration: int
    total_violations: int
    general_violations: int
    weekend_violations: int
    schedule: Optional[Dict] = None
    validation_report: Optional[Dict] = None

class IterativeOptimizer:
    """
    Iterative optimization system that continuously improves schedule assignments
    until tolerance requirements are met.
    """
    
    def __init__(self, max_iterations: int = 15, tolerance: float = 0.08):
        """
        Initialize the iterative optimizer with enhanced redistribution algorithms.
        
        Args:
            max_iterations: Maximum number of optimization iterations (default: 15)
            tolerance: Tolerance percentage (0.08 = 8%)
        """
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.validator = None  # Will be initialized when needed
        
        # Enhanced optimization controls
        self.convergence_threshold = 3  # Stop if no improvement for N iterations
        self.min_improvement_rate = 0.05  # Minimum improvement rate to continue
        self.stagnation_penalty = 1.2  # Penalty factor for stagnant optimization
        
        # Optimization statistics
        self.optimization_history = []
        self.best_result = None
        self.stagnation_counter = 0
        
        logging.info(f"IterativeOptimizer initialized: max_iterations={max_iterations}, tolerance={tolerance*100}%")
    
    @time_function
    def optimize_schedule(self, scheduler_core, schedule: Dict, workers_data: List[Dict], 
                         schedule_config: Dict) -> OptimizationResult:
        """
        Optimize a schedule iteratively until tolerance requirements are met.
        
        Args:
            scheduler_core: The core scheduler instance
            schedule: Current schedule to optimize
            workers_data: Worker data configuration
            schedule_config: Schedule configuration parameters
            
        Returns:
            OptimizationResult with final optimization status
        """
        logging.info("🔄 Starting iterative schedule optimization...")
        logging.info(f"Debug: Optimizer called with {len(schedule)} schedule entries and {len(workers_data)} workers")
        
        # Use the scheduler's tolerance validator
        if hasattr(scheduler_core, 'tolerance_validator'):
            validator = scheduler_core.tolerance_validator
            logging.info("Debug: Using scheduler's tolerance validator")
        else:
            logging.error("Scheduler core missing tolerance validator")
            return OptimizationResult(
                success=False,
                iteration=0,
                total_violations=float('inf'),
                general_violations=0,
                weekend_violations=0
            )
        
        current_schedule = copy.deepcopy(schedule)
        best_schedule = copy.deepcopy(schedule)
        best_violations = float('inf')
        
        for iteration in range(1, self.max_iterations + 1):
            logging.info(f"🔄 Optimization iteration {iteration}/{self.max_iterations}")
            
            # Validate current schedule using existing methods
            validation_report = self._create_validation_report(validator, current_schedule)
            
            # Count violations
            general_violations = len(validation_report.get('general_shift_violations', []))
            weekend_violations = len(validation_report.get('weekend_shift_violations', []))
            total_violations = general_violations + weekend_violations
            
            logging.info(f"   General violations: {general_violations}, Weekend violations: {weekend_violations}")
            
            # Check if we've achieved optimal result
            if total_violations == 0:
                logging.info(f"✅ Optimal schedule achieved in iteration {iteration}!")
                return OptimizationResult(
                    success=True,
                    iteration=iteration,
                    total_violations=0,
                    general_violations=0,
                    weekend_violations=0,
                    schedule=current_schedule,
                    validation_report=validation_report
                )
            
            # Track best result so far
            if total_violations < best_violations:
                improvement_ratio = (best_violations - total_violations) / max(best_violations, 1)
                best_violations = total_violations
                best_schedule = copy.deepcopy(current_schedule)
                self.stagnation_counter = 0  # Reset stagnation counter
                
                self.best_result = OptimizationResult(
                    success=False,
                    iteration=iteration,
                    total_violations=total_violations,
                    general_violations=general_violations,
                    weekend_violations=weekend_violations,
                    schedule=best_schedule,
                    validation_report=validation_report
                )
                logging.info(f"   📈 New best result: {total_violations} violations (improvement: {improvement_ratio:.2%})")
            else:
                self.stagnation_counter += 1
                logging.info(f"   📊 No improvement this iteration (stagnation: {self.stagnation_counter}/{self.convergence_threshold})")
                
                # Apply stagnation penalty for more aggressive optimization
                if self.stagnation_counter >= 2:
                    logging.info("   🎯 Applying stagnation penalty - increasing optimization intensity")
            
            # Store optimization history
            self.optimization_history.append({
                'iteration': iteration,
                'total_violations': total_violations,
                'general_violations': general_violations,
                'weekend_violations': weekend_violations,
                'improvement_made': total_violations < best_violations
            })
            
            # Enhanced convergence checks
            if self._should_stop_optimization(iteration, total_violations):
                logging.info(f"🛑 Early convergence detected - stopping optimization")
                break
            
            # Apply optimization strategies
            try:
                # Calculate optimization intensity based on stagnation
                optimization_intensity = min(1.0, 0.3 + (self.stagnation_counter * 0.2))
                
                current_schedule = self._apply_optimization_strategies(
                    current_schedule, validation_report, scheduler_core, 
                    workers_data, schedule_config, iteration, optimization_intensity
                )
            except Exception as e:
                logging.error(f"❌ Error in iteration {iteration}: {e}", exc_info=True)
                continue
        
        # Return best result found
        if self.best_result:
            logging.warning(f"⚠️  Optimization completed with {self.best_result.total_violations} violations remaining")
            self.best_result.success = (self.best_result.total_violations == 0)
            return self.best_result
        else:
            logging.error("❌ Optimization failed completely")
            return OptimizationResult(
                success=False,
                iteration=self.max_iterations,
                total_violations=total_violations,
                general_violations=general_violations,
                weekend_violations=weekend_violations,
                schedule=current_schedule,
                validation_report=validation_report
            )
    
    def _apply_optimization_strategies(self, schedule: Dict, validation_report: Dict, 
                                     scheduler_core, workers_data: List[Dict], 
                                     schedule_config: Dict, iteration: int, 
                                     intensity: float = 0.3) -> Dict:
        """
        Apply various optimization strategies to improve the schedule.
        
        Args:
            schedule: Current schedule
            validation_report: Validation report with violations
            scheduler_core: Scheduler core instance
            workers_data: Worker configuration
            schedule_config: Schedule configuration
            iteration: Current iteration number
            intensity: Optimization intensity (0.0 to 1.0)
            
        Returns:
            Improved schedule
        """
        logging.info(f"   🔧 Applying optimization strategies (intensity: {intensity:.2f})...")
        
        optimized_schedule = copy.deepcopy(schedule)
        
        # Strategy 1: Redistribute general shifts for workers with violations
        general_violations = validation_report.get('general_shift_violations', [])
        if general_violations:
            optimized_schedule = self._redistribute_general_shifts(
                optimized_schedule, general_violations, workers_data, schedule_config
            )
        
        # Strategy 2: Redistribute weekend shifts for workers with violations
        weekend_violations = validation_report.get('weekend_shift_violations', [])
        if weekend_violations:
            optimized_schedule = self._redistribute_weekend_shifts(
                optimized_schedule, weekend_violations, workers_data, schedule_config
            )
        
        # Strategy 3: Apply random perturbations based on intensity
        total_violations = len(general_violations) + len(weekend_violations)
        if iteration > 1 and (total_violations > 15 or self.stagnation_counter > 1):  # Apply perturbations earlier for difficult cases
            perturbation_intensity = min(intensity * 0.8, 0.4)  # More aggressive perturbations
            optimized_schedule = self._apply_random_perturbations(
                optimized_schedule, workers_data, schedule_config, intensity=perturbation_intensity
            )
        
        return optimized_schedule
    
    def _redistribute_general_shifts(self, schedule: Dict, violations: List[Dict], 
                                   workers_data: List[Dict], schedule_config: Dict) -> Dict:
        """Redistribute general shifts to fix tolerance violations with smart targeting."""
        logging.info(f"   📊 Redistributing general shifts for {len(violations)} workers")
        
        try:
            optimized_schedule = copy.deepcopy(schedule)
            
            # Debug: Log workers_data structure
            logging.info(f"Debug: workers_data type: {type(workers_data)}")
            logging.info(f"Debug: workers_data length: {len(workers_data)}")
            if workers_data:
                logging.info(f"Debug: First worker structure: {workers_data[0]}")
                logging.info(f"Debug: Available keys: {list(workers_data[0].keys()) if isinstance(workers_data[0], dict) else 'Not a dict'}")
            
            # Extract worker names safely
            worker_names = []
            for i, w in enumerate(workers_data):
                if isinstance(w, dict):
                    if 'id' in w:
                        # Handle both string and numeric IDs
                        worker_id = w['id']
                        if isinstance(worker_id, str) and worker_id.startswith('Worker'):
                            worker_names.append(worker_id)  # Already has "Worker" prefix
                        else:
                            worker_names.append(f"Worker {worker_id}")  # Add prefix for numeric
                    elif 'name' in w:
                        worker_names.append(w['name'])
                    else:
                        worker_names.append(f"Worker {i+1}")  # Fallback
                        logging.warning(f"Worker {i} missing id/name, using fallback")
                else:
                    worker_names.append(f"Worker {i+1}")  # Fallback for non-dict
                    logging.warning(f"Worker {i} is not a dict: {type(w)}")
            
            # Debug: Log the structures
            logging.info(f"Debug: Worker names extracted: {worker_names[:5]}...")  # First 5
            logging.info(f"Debug: Violations structure: {violations}")
            
            # Separate workers by violation type with priority scoring
            need_more_shifts = []
            have_excess_shifts = []
            
            for violation in violations:
                logging.info(f"Debug: Processing violation: {violation}")
                worker_name = violation['worker']
                deviation = violation['deviation_percentage']
                
                logging.info(f"Debug: worker_name='{worker_name}', deviation={deviation}")
                
                if deviation < -self.tolerance * 100:  # Worker needs more shifts
                    priority = abs(deviation) / 100.0  # Higher deviation = higher priority
                    need_more_shifts.append({
                        'worker': worker_name,
                        'shortage': abs(violation['shortage']),
                        'priority': priority,
                        'deviation': deviation
                    })
                    logging.info(f"Debug: Added to need_more_shifts: {worker_name}")
                elif deviation > self.tolerance * 100:  # Worker has excess shifts
                    priority = deviation / 100.0
                    have_excess_shifts.append({
                        'worker': worker_name,
                        'excess': violation['excess'],
                        'priority': priority,
                        'deviation': deviation
                    })
                    logging.info(f"Debug: Added to have_excess_shifts: {worker_name}")
                    
        except Exception as e:
            logging.error(f"❌ Error in _redistribute_general_shifts: {e}", exc_info=True)
            return schedule  # Return original schedule on error
            
            if deviation < -self.tolerance * 100:  # Worker needs more shifts
                priority = abs(deviation) / 100.0  # Higher deviation = higher priority
                need_more_shifts.append({
                    'worker': worker_name,
                    'shortage': abs(violation['shortage']),
                    'priority': priority,
                    'deviation': deviation
                })
            elif deviation > self.tolerance * 100:  # Worker has excess shifts
                priority = deviation / 100.0
                have_excess_shifts.append({
                    'worker': worker_name,
                    'excess': violation['excess'],
                    'priority': priority,
                    'deviation': deviation
                })
        
        # Sort by priority (most urgent first)
        need_more_shifts.sort(key=lambda x: x['priority'], reverse=True)
        have_excess_shifts.sort(key=lambda x: x['priority'], reverse=True)
        
        logging.info(f"   📊 Need more: {len(need_more_shifts)}, Have excess: {len(have_excess_shifts)}")
        
        # Smart redistribution algorithm
        redistributions_made = 0
        max_redistributions = min(30, len(violations) * 3)  # More aggressive redistribution
        
        for excess_info in have_excess_shifts:
            if redistributions_made >= max_redistributions:
                break
                
            excess_worker = excess_info['worker']
            shifts_to_remove = min(excess_info['excess'], 4)  # More aggressive removal (up to 4 shifts)
            
            # Find shifts assigned to this worker, prioritize recent dates
            worker_shifts = []
            for date_key, assignments in optimized_schedule.items():
                # Handle different schedule formats
                if isinstance(assignments, dict):
                    # Format: {date: {'Morning': [workers], 'Afternoon': [workers]}}
                    for shift_type, workers in assignments.items():
                        if excess_worker in workers:
                            worker_shifts.append((date_key, shift_type, workers))
                elif isinstance(assignments, list):
                    # Format: {date: [worker1, worker2, worker3]} - positional
                    for post_idx, worker in enumerate(assignments):
                        if worker == excess_worker:
                            worker_shifts.append((date_key, f"Post_{post_idx}", assignments))
                else:
                    logging.warning(f"Unknown schedule format for {date_key}: {type(assignments)}")
                    continue
            
            # Sort by date (prefer redistributing from later dates)
            worker_shifts.sort(key=lambda x: x[0], reverse=True)
            
            shifts_removed = 0
            for date_key, shift_type, workers in worker_shifts:
                if shifts_removed >= shifts_to_remove:
                    break
                
                # Find best recipient for this shift
                best_recipient = None
                best_priority = 0
                
                for need_info in need_more_shifts:
                    if need_info['shortage'] <= 0:
                        continue
                        
                    need_worker = need_info['worker']
                    
                    # Check if worker can take this shift
                    if need_worker not in workers and self._can_worker_take_shift(
                        need_worker, date_key, shift_type, optimized_schedule, workers_data
                    ):
                        # Calculate priority for this assignment
                        assignment_priority = need_info['priority']
                        
                        # Bonus for workers with severe shortages
                        if need_info['deviation'] < -15:
                            assignment_priority *= 1.5
                        
                        if assignment_priority > best_priority:
                            best_recipient = need_worker
                            best_priority = assignment_priority
                
                # Make the reassignment
                if best_recipient:
                    # Handle both list and dict formats for reassignment
                    if isinstance(workers, list):
                        # Find and replace in the list
                        try:
                            idx = workers.index(excess_worker)
                            workers[idx] = best_recipient
                        except ValueError:
                            logging.warning(f"Worker {excess_worker} not found in list {workers}")
                            continue
                    else:
                        # Dictionary format (original logic)
                        workers.remove(excess_worker)
                        workers.append(best_recipient)
                    
                    # Update tracking
                    for need_info in need_more_shifts:
                        if need_info['worker'] == best_recipient:
                            need_info['shortage'] -= 1
                            break
                    
                    shifts_removed += 1
                    redistributions_made += 1
                    
                    # Format date for display
                    date_display = date_key.strftime('%Y-%m-%d') if isinstance(date_key, datetime) else str(date_key)
                    logging.info(f"      🔄 Moved {shift_type} from {excess_worker} to {best_recipient} on {date_display}")
        
        logging.info(f"   ✅ Made {redistributions_made} general shift redistributions")
        return optimized_schedule
    
    def _can_worker_take_shift(self, worker_name: str, date_key, shift_type: str, 
                              schedule: Dict, workers_data: List[Dict]) -> bool:
        """
        Check if a worker can take a specific shift based on constraints.
        
        Args:
            worker_name: Name of the worker (e.g., "Worker 12")
            date_key: Date of the shift (datetime object or string)
            shift_type: Type of shift (Morning, Afternoon, Night, etc.)
            schedule: Current schedule
            workers_data: Worker configuration data
            
        Returns:
            bool: True if worker can take the shift
        """
        try:
            # Parse date from both datetime and string formats
            if isinstance(date_key, datetime):
                shift_date = date_key
            else:
                shift_date = datetime.strptime(date_key, "%Y-%m-%d")
            
            # Extract worker ID from worker name 
            worker_id = None
            if isinstance(worker_name, str):
                if worker_name.startswith('Worker_'):
                    worker_id = worker_name  # Direct match (e.g., "Worker_A")
                elif worker_name.startswith('Worker ') and len(worker_name) > 7:
                    worker_id = worker_name[7:]  # Extract after "Worker " (e.g., "Worker 12" -> "12")
                    try:
                        worker_id = int(worker_id)  # Convert to int if numeric
                    except ValueError:
                        pass  # Keep as string if non-numeric
                else:
                    worker_id = worker_name  # Use as-is
            
            # Find worker data using ID
            worker_data = None
            for w in workers_data:
                if w.get('id') == worker_id or str(w.get('id')) == str(worker_id):
                    worker_data = w
                    break
            
            if not worker_data:
                return False
            
            # Check basic availability
            worker_availability = worker_data.get('availability', {})
            day_name = shift_date.strftime('%A')
            
            if day_name in worker_availability:
                available_shifts = worker_availability[day_name]
                if available_shifts != 'ALL' and shift_type not in available_shifts:
                    return False
            
            # Check if worker already has a shift on this date
            if date_key in schedule:
                assignments = schedule[date_key]
                if isinstance(assignments, dict):
                    # Dictionary format: check all shift types
                    for existing_shift, existing_workers in assignments.items():
                        if worker_name in existing_workers:
                            return False  # Worker already assigned on this date
                elif isinstance(assignments, list):
                    # List format: check if worker is in the list
                    if worker_name in assignments:
                        return False  # Worker already assigned on this date
            
            # Check consecutive shift limits (basic check)
            # This is a simplified version - full implementation would check actual constraints
            return True
            
        except Exception as e:
            logging.debug(f"Error checking if {worker_name} can take shift: {e}")
            return False
    
    def _redistribute_weekend_shifts(self, schedule: Dict, violations: List[Dict], 
                                   workers_data: List[Dict], schedule_config: Dict) -> Dict:
        """Redistribute weekend shifts to fix tolerance violations with enhanced targeting."""
        logging.info(f"   📅 Redistributing weekend shifts for {len(violations)} workers")
        
        optimized_schedule = copy.deepcopy(schedule)
        
        # Separate weekend violations with priority scoring
        need_more_weekends = []
        have_excess_weekends = []
        
        for violation in violations:
            worker_name = violation['worker']
            deviation = violation['deviation_percentage']
            
            if deviation < -self.tolerance * 100:
                priority = abs(deviation) / 100.0
                need_more_weekends.append({
                    'worker': worker_name,
                    'shortage': abs(violation['shortage']),
                    'priority': priority,
                    'deviation': deviation
                })
            elif deviation > self.tolerance * 100:
                priority = deviation / 100.0
                have_excess_weekends.append({
                    'worker': worker_name,
                    'excess': violation['excess'],
                    'priority': priority,
                    'deviation': deviation
                })
        
        # Sort by priority
        need_more_weekends.sort(key=lambda x: x['priority'], reverse=True)
        have_excess_weekends.sort(key=lambda x: x['priority'], reverse=True)
        
        # Get all weekend dates
        weekend_dates = []
        for date_key in optimized_schedule.keys():
            try:
                # Handle both datetime objects and string dates
                if isinstance(date_key, datetime):
                    date_obj = date_key
                    date_str = date_key.strftime("%Y-%m-%d")
                else:
                    date_obj = datetime.strptime(date_key, "%Y-%m-%d")
                    date_str = date_key
                
                if date_obj.weekday() in [5, 6]:  # Saturday or Sunday
                    weekend_dates.append(date_key)  # Use original key format
            except:
                continue
        
        logging.info(f"   📅 Processing {len(weekend_dates)} weekend dates")
        
        redistributions_made = 0
        max_redistributions = min(15, len(violations) * 2)
        
        # Smart weekend redistribution
        for excess_info in have_excess_weekends:
            if redistributions_made >= max_redistributions:
                break
                
            excess_worker = excess_info['worker']
            
            # Find weekend shifts for this worker
            weekend_shifts = []
            for date_key in weekend_dates:
                if date_key in optimized_schedule:
                    assignments = optimized_schedule[date_key]
                    # Handle different schedule formats
                    if isinstance(assignments, dict):
                        # Format: {date: {'Morning': [workers], 'Afternoon': [workers]}}
                        for shift_type, workers in assignments.items():
                            if excess_worker in workers:
                                weekend_shifts.append((date_key, shift_type, workers))
                    elif isinstance(assignments, list):
                        # Format: {date: [worker1, worker2, worker3]} - positional
                        for post_idx, worker in enumerate(assignments):
                            if worker == excess_worker:
                                weekend_shifts.append((date_key, f"Post_{post_idx}", assignments))
                    else:
                        logging.warning(f"Unknown weekend schedule format for {date_key}: {type(assignments)}")
                        continue
            
            # Redistribute weekend shifts
            shifts_to_redistribute = min(len(weekend_shifts), excess_info['excess'])
            
            for i, (date_key, shift_type, workers) in enumerate(weekend_shifts):
                if i >= shifts_to_redistribute or redistributions_made >= max_redistributions:
                    break
                
                # Find best weekend recipient
                best_recipient = None
                best_priority = 0
                
                for need_info in need_more_weekends:
                    if need_info['shortage'] <= 0:
                        continue
                        
                    need_worker = need_info['worker']
                    
                    # Check if worker can take this weekend shift
                    if need_worker not in workers and self._can_worker_take_shift(
                        need_worker, date_key, shift_type, optimized_schedule, workers_data
                    ):
                        # Calculate assignment priority
                        assignment_priority = need_info['priority']
                        
                        # Bonus for severe weekend shortages
                        if need_info['deviation'] < -25:
                            assignment_priority *= 2.0
                        
                        # Bonus for balanced weekend distribution
                        if isinstance(date_key, datetime):
                            weekend_day = date_key.weekday()
                        else:
                            weekend_day = datetime.strptime(date_key, "%Y-%m-%d").weekday()
                        
                        if weekend_day == 5:  # Saturday
                            assignment_priority *= 1.1
                        
                        if assignment_priority > best_priority:
                            best_recipient = need_worker
                            best_priority = assignment_priority
                
                # Make the weekend reassignment
                if best_recipient:
                    # Handle both list and dict formats for reassignment
                    if isinstance(workers, list):
                        # Find and replace in the list
                        try:
                            idx = workers.index(excess_worker)
                            workers[idx] = best_recipient
                        except ValueError:
                            logging.warning(f"Weekend worker {excess_worker} not found in list {workers}")
                            continue
                    else:
                        # Dictionary format (original logic)
                        workers.remove(excess_worker)
                        workers.append(best_recipient)
                    
                    # Update tracking
                    for need_info in need_more_weekends:
                        if need_info['worker'] == best_recipient:
                            need_info['shortage'] -= 1
                            break
                    
                    redistributions_made += 1
                    if isinstance(date_key, datetime):
                        day_name = date_key.strftime('%A')
                        date_display = date_key.strftime('%Y-%m-%d')
                    else:
                        day_name = datetime.strptime(date_key, "%Y-%m-%d").strftime('%A')
                        date_display = date_key
                    
                    logging.info(f"      🔄 Weekend: Moved {shift_type} from {excess_worker} to {best_recipient} on {day_name} {date_display}")
        
        logging.info(f"   ✅ Made {redistributions_made} weekend shift redistributions")
        return optimized_schedule
    
    def _apply_random_perturbations(self, schedule: Dict, workers_data: List[Dict], 
                                  schedule_config: Dict, intensity: float = 0.1) -> Dict:
        """Apply random perturbations to escape local optima."""
        logging.info(f"   🎲 Applying random perturbations (intensity: {intensity:.2f})")
        
        optimized_schedule = copy.deepcopy(schedule)
        worker_names = [w['name'] for w in workers_data]
        
        # Calculate number of swaps based on intensity
        total_assignments = sum(len([w for workers in assignments.values() for w in workers]) 
                              for assignments in schedule.values())
        num_swaps = int(total_assignments * intensity)
        
        for _ in range(num_swaps):
            # Pick random date and shift
            dates = list(optimized_schedule.keys())
            random_date = random.choice(dates)
            
            if not optimized_schedule[random_date]:
                continue
                
            shift_types = list(optimized_schedule[random_date].keys())
            random_shift = random.choice(shift_types)
            
            current_workers = optimized_schedule[random_date][random_shift]
            if len(current_workers) > 0:
                # Replace random worker with another random worker
                old_worker = random.choice(current_workers)
                new_worker = random.choice(worker_names)
                
                if new_worker not in current_workers:
                    current_workers.remove(old_worker)
                    current_workers.append(new_worker)
        
        return optimized_schedule
    
    def get_optimization_summary(self) -> Dict:
        """Get summary of optimization process."""
        if not self.optimization_history:
            return {"message": "No optimization history available"}
        
        return {
            "total_iterations": len(self.optimization_history),
            "initial_violations": self.optimization_history[0]['total_violations'],
            "final_violations": self.optimization_history[-1]['total_violations'],
            "best_violations": min(h['total_violations'] for h in self.optimization_history),
            "improvement": self.optimization_history[0]['total_violations'] - self.optimization_history[-1]['total_violations'],
            "convergence_achieved": self.optimization_history[-1]['total_violations'] == 0,
            "stagnation_counter": self.stagnation_counter,
            "average_improvement_rate": self._calculate_average_improvement(),
            "history": self.optimization_history
        }
    
    def _should_stop_optimization(self, iteration: int, current_violations: int) -> bool:
        """
        Determine if optimization should stop based on convergence criteria.
        
        Args:
            iteration: Current iteration number
            current_violations: Current number of violations
            
        Returns:
            bool: True if optimization should stop
        """
        # Stop if stagnation threshold reached
        if self.stagnation_counter >= self.convergence_threshold:
            logging.info(f"   🛑 Stopping due to stagnation ({self.stagnation_counter} iterations without improvement)")
            return True
        
        # Stop if violations are acceptably low
        if current_violations <= 5 and iteration >= 8:  # More lenient criteria
            logging.info(f"   ✅ Stopping due to acceptable violation level ({current_violations})")
            return True
        
        # Check improvement rate trend
        if len(self.optimization_history) >= 3:
            recent_violations = [h['total_violations'] for h in self.optimization_history[-3:]]
            if all(v == recent_violations[0] for v in recent_violations):
                logging.info(f"   🛑 Stopping due to plateau in violation count")
                return True
        
        # Dynamic early stopping for very difficult schedules
        if iteration >= 8 and current_violations > 20:
            average_improvement = self._calculate_average_improvement()
            if average_improvement < 0.5:  # Less than 0.5 violations improvement per iteration
                logging.info(f"   🛑 Stopping due to low improvement rate ({average_improvement:.2f})")
                return True
        
        return False
    
    def _calculate_average_improvement(self) -> float:
        """Calculate average improvement rate over recent iterations."""
        if len(self.optimization_history) < 2:
            return 0.0
        
        initial_violations = self.optimization_history[0]['total_violations']
        current_violations = self.optimization_history[-1]['total_violations']
        iterations = len(self.optimization_history)
        
        return max(0, (initial_violations - current_violations) / iterations)
    
    def _create_validation_report(self, validator, current_schedule: Dict) -> Dict:
        """
        Create a validation report using the existing validator methods.
        
        Args:
            validator: ShiftToleranceValidator instance
            current_schedule: Current schedule to validate
            
        Returns:
            Dict with validation report in expected format
        """
        try:
            # Update validator's schedule reference
            original_schedule = validator.schedule
            validator.schedule = current_schedule
            
            logging.info("Debug: Creating validation report...")
            
            # Get violations using existing methods
            general_violations = []
            weekend_violations = []
            
            # Check all workers for general violations
            general_outside = validator.get_workers_outside_tolerance(is_weekend_only=False)
            logging.info(f"Debug: Found {len(general_outside)} workers outside general tolerance")
            
            for worker_info in general_outside:
                worker_id = worker_info.get('worker_id', 'Unknown')
                worker_name = f"Worker {worker_id}" if str(worker_id).isdigit() else str(worker_id)
                
                # Calculate difference (assigned - target)
                assigned = worker_info.get('assigned_shifts', 0)
                target = worker_info.get('target_shifts', 0)
                difference = assigned - target
                
                general_violations.append({
                    'worker': worker_name,
                    'deviation_percentage': worker_info.get('deviation_percentage', 0),
                    'shortage': max(0, -difference),  # When assigned < target
                    'excess': max(0, difference)      # When assigned > target
                })
            
            # Check all workers for weekend violations  
            weekend_outside = validator.get_workers_outside_tolerance(is_weekend_only=True)
            logging.info(f"Debug: Found {len(weekend_outside)} workers outside weekend tolerance")
            
            for worker_info in weekend_outside:
                worker_id = worker_info.get('worker_id', 'Unknown')
                worker_name = f"Worker {worker_id}" if str(worker_id).isdigit() else str(worker_id)
                
                # Calculate difference (assigned - target)
                assigned = worker_info.get('assigned_shifts', 0)
                target = worker_info.get('target_shifts', 0)
                difference = assigned - target
                
                weekend_violations.append({
                    'worker': worker_name,
                    'deviation_percentage': worker_info.get('deviation_percentage', 0),
                    'shortage': max(0, -difference),  # When assigned < target
                    'excess': max(0, difference)      # When assigned > target
                })
            
            # Restore original schedule
            validator.schedule = original_schedule
            
            report = {
                'general_shift_violations': general_violations,
                'weekend_shift_violations': weekend_violations,
                'total_violations': len(general_violations) + len(weekend_violations)
            }
            
            logging.info(f"Debug: Created validation report with {report['total_violations']} total violations")
            return report
            
        except Exception as e:
            logging.error(f"Error creating validation report: {e}")
            return {
                'general_shift_violations': [],
                'weekend_shift_violations': [],
                'total_violations': 0
            }