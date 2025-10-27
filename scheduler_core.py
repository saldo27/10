"""
Scheduler Core Module

This module contains the main orchestration logic for the scheduler system,
extracted from the original Scheduler class to improve maintainability and separation of concerns.
"""

import logging
import copy
import random
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple, Any

from scheduler_config import SchedulerConfig
from exceptions import SchedulerError
from optimization_metrics import OptimizationMetrics
from operation_prioritizer import OperationPrioritizer
from progress_monitor import ProgressMonitor
from iterative_optimizer import IterativeOptimizer
from shift_tolerance_validator import ShiftToleranceValidator
from adaptive_iterations import AdaptiveIterationManager


class SchedulerCore:
    """
    Core orchestration class that manages the high-level scheduling workflow.
    This class focuses on coordination between components rather than implementation details.
    """
    
    def __init__(self, scheduler):
        """
        Initialize the scheduler core with enhanced optimization systems.
        
        Args:
            scheduler: Reference to the main Scheduler instance
        """
        self.scheduler = scheduler
        self.config = scheduler.config
        self.start_date = scheduler.start_date
        self.end_date = scheduler.end_date
        self.workers_data = scheduler.workers_data
        
        # Initialize enhancement systems
        self.metrics = OptimizationMetrics(scheduler)
        self.prioritizer = OperationPrioritizer(scheduler, self.metrics)
        self.progress_monitor = None  # Will be initialized in orchestrate_schedule_generation
        
        # Initialize tolerance validation and iterative optimization
        self.tolerance_validator = ShiftToleranceValidator(scheduler)
        self.iterative_optimizer = IterativeOptimizer(max_iterations=20, tolerance=0.08)
        
        # Initialize adaptive iteration manager for intelligent optimization
        self.adaptive_manager = AdaptiveIterationManager(scheduler)
        
        logging.info("SchedulerCore initialized with enhanced optimization systems and tolerance validation")
    
    def orchestrate_schedule_generation(self, max_improvement_loops: int = 70) -> bool:
        """
        Main orchestration method for schedule generation workflow.
        
        Args:
            max_improvement_loops: Maximum number of improvement iterations
            
        Returns:
            bool: True if schedule generation was successful
        """
        logging.info("Starting schedule generation orchestration...")
        start_time = datetime.now()
        
        try:
            # Phase 1: Initialize schedule structure
            if not self._initialize_schedule_phase():
                raise SchedulerError("Failed to initialize schedule structure")
            
            # Phase 2: Assign mandatory shifts
            if not self._assign_mandatory_phase():
                raise SchedulerError("Failed to assign mandatory shifts")
            
            # Phase 2.5: Multiple initial distribution attempts (NEW)
            if not self._multiple_initial_distribution_attempts():
                logging.warning("Multiple initial attempts phase completed with issues")
            
            # Phase 3: Iterative improvement
            if not self._iterative_improvement_phase(max_improvement_loops):
                logging.warning("Iterative improvement phase completed with issues")
            
            # Phase 4: Finalization
            if not self._finalization_phase():
                raise SchedulerError("Failed to finalize schedule")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logging.info(f"Schedule generation orchestration completed successfully in {duration:.2f} seconds.")
            return True
            
        except Exception as e:
            logging.error(f"Schedule generation orchestration failed: {str(e)}", exc_info=True)
            if isinstance(e, SchedulerError):
                raise e
            else:
                raise SchedulerError(f"Orchestration failed: {str(e)}")
    
    def _initialize_schedule_phase(self) -> bool:
        """
        Phase 1: Initialize schedule structure and data.
        
        Returns:
            bool: True if initialization was successful
        """
        logging.info("Phase 1: Initializing schedule structure...")
        
        try:
            # Reset scheduler state
            self.scheduler.schedule = {}
            self.scheduler.worker_assignments = {w['id']: set() for w in self.workers_data}
            self.scheduler.worker_shift_counts = {w['id']: 0 for w in self.workers_data}
            self.scheduler.worker_weekend_counts = {w['id']: 0 for w in self.workers_data}
            self.scheduler.worker_posts = {w['id']: set() for w in self.workers_data}
            self.scheduler.last_assignment_date = {w['id']: None for w in self.workers_data}
            self.scheduler.consecutive_shifts = {w['id']: 0 for w in self.workers_data}
            
            # Initialize schedule with variable shifts
            self.scheduler._initialize_schedule_with_variable_shifts()
            
            # Create schedule builder
            from schedule_builder import ScheduleBuilder
            self.scheduler.schedule_builder = ScheduleBuilder(self.scheduler)
            
            logging.info(f"Schedule structure initialized with {len(self.scheduler.schedule)} dates")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize schedule phase: {str(e)}", exc_info=True)
            return False
    
    def _assign_mandatory_phase(self) -> bool:
        """
        Phase 2: Assign mandatory shifts and lock them in place.
        
        Returns:
            bool: True if mandatory assignment was successful
        """
        logging.info("Phase 2: Assigning mandatory shifts...")
        
        try:
            # Pre-assign mandatory shifts
            self.scheduler.schedule_builder._assign_mandatory_guards()
            
            # Synchronize tracking data
            self.scheduler.schedule_builder._synchronize_tracking_data()
            
            # Save initial state as best
            self.scheduler.schedule_builder._save_current_as_best(initial=True)
            
            # Log summary
            self.scheduler.log_schedule_summary("After Mandatory Assignment")
            
            logging.info("Mandatory assignment phase completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed in mandatory assignment phase: {str(e)}", exc_info=True)
            return False
    
    def _multiple_initial_distribution_attempts(self) -> bool:
        """
        Phase 2.5: Perform multiple initial distribution attempts with different strategies
        and select the best one based on quality score.
        
        This phase uses AdaptiveIterationManager to determine how many attempts to make
        based on problem complexity. Each attempt uses a different strategy:
        - Random seed variation
        - Different worker ordering
        - Different post assignment priorities
        
        Returns:
            bool: True if at least one attempt was successful
        """
        logging.info("=" * 80)
        logging.info("Phase 2.5: Multiple Initial Distribution Attempts")
        logging.info("=" * 80)
        
        try:
            # Get adaptive configuration to determine number of attempts
            adaptive_config = self.adaptive_manager.calculate_adaptive_iterations()
            
            # Determine number of initial attempts based on complexity
            complexity_score = adaptive_config.get('complexity_score', 0)
            
            if complexity_score < 1000:
                num_attempts = 3
            elif complexity_score < 5000:
                num_attempts = 5
            elif complexity_score < 15000:
                num_attempts = 7
            else:
                num_attempts = 10
            
            logging.info(f"Problem complexity: {complexity_score:.0f}")
            logging.info(f"Number of initial distribution attempts: {num_attempts}")
            
            # Save current mandatory state (this must be preserved)
            mandatory_backup = copy.deepcopy(self.scheduler.schedule)
            mandatory_assignments = copy.deepcopy(self.scheduler.worker_assignments)
            mandatory_counts = copy.deepcopy(self.scheduler.worker_shift_counts)
            mandatory_weekend_counts = copy.deepcopy(self.scheduler.worker_weekend_counts)
            mandatory_posts = copy.deepcopy(self.scheduler.worker_posts)
            
            best_attempt = None
            best_score = -1
            attempts_results = []
            
            # Start adaptive iteration manager timer
            self.adaptive_manager.start_time = datetime.now()
            
            for attempt_num in range(1, num_attempts + 1):
                logging.info(f"\n{'─' * 80}")
                logging.info(f"🔄 Initial Distribution Attempt {attempt_num}/{num_attempts}")
                logging.info(f"{'─' * 80}")
                
                # Restore mandatory state
                self.scheduler.schedule = copy.deepcopy(mandatory_backup)
                self.scheduler.worker_assignments = copy.deepcopy(mandatory_assignments)
                self.scheduler.worker_shift_counts = copy.deepcopy(mandatory_counts)
                self.scheduler.worker_weekend_counts = copy.deepcopy(mandatory_weekend_counts)
                self.scheduler.worker_posts = copy.deepcopy(mandatory_posts)
                
                # Apply different strategy for each attempt
                strategy = self._select_distribution_strategy(attempt_num, num_attempts)
                logging.info(f"Strategy for attempt {attempt_num}: {strategy['name']}")
                
                # Perform initial fill with this strategy
                success = self._perform_initial_fill_with_strategy(strategy)
                
                if not success:
                    logging.warning(f"Attempt {attempt_num} failed to fill schedule")
                    attempts_results.append({
                        'attempt': attempt_num,
                        'strategy': strategy['name'],
                        'success': False,
                        'score': 0
                    })
                    continue
                
                # Calculate quality score for this attempt
                score = self.metrics.calculate_overall_schedule_score()
                
                # Get detailed metrics
                empty_shifts = self.metrics.count_empty_shifts()
                workload_imbalance = self.metrics.calculate_workload_imbalance()
                weekend_imbalance = self.metrics.calculate_weekend_imbalance()
                
                logging.info(f"📊 Attempt {attempt_num} Results:")
                logging.info(f"   Overall Score: {score:.2f}")
                logging.info(f"   Empty Shifts: {empty_shifts}")
                logging.info(f"   Workload Imbalance: {workload_imbalance:.2f}")
                logging.info(f"   Weekend Imbalance: {weekend_imbalance:.2f}")
                
                # Record this attempt
                attempts_results.append({
                    'attempt': attempt_num,
                    'strategy': strategy['name'],
                    'success': True,
                    'score': score,
                    'empty_shifts': empty_shifts,
                    'workload_imbalance': workload_imbalance,
                    'weekend_imbalance': weekend_imbalance
                })
                
                # Check if this is the best so far
                if score > best_score:
                    best_score = score
                    best_attempt = attempt_num
                    # Save this as the best attempt
                    best_schedule = copy.deepcopy(self.scheduler.schedule)
                    best_assignments = copy.deepcopy(self.scheduler.worker_assignments)
                    best_counts = copy.deepcopy(self.scheduler.worker_shift_counts)
                    best_weekend_counts = copy.deepcopy(self.scheduler.worker_weekend_counts)
                    best_posts = copy.deepcopy(self.scheduler.worker_posts)
                    
                    logging.info(f"✨ New best attempt! Score: {score:.2f}")
            
            # Summary of all attempts
            logging.info(f"\n{'=' * 80}")
            logging.info("📈 INITIAL DISTRIBUTION ATTEMPTS SUMMARY")
            logging.info(f"{'=' * 80}")
            
            successful_attempts = [r for r in attempts_results if r['success']]
            
            if not successful_attempts:
                logging.error("❌ All initial distribution attempts failed!")
                return False
            
            logging.info(f"Successful attempts: {len(successful_attempts)}/{num_attempts}")
            
            # Display results table
            logging.info(f"\n{'Attempt':<10} {'Strategy':<25} {'Score':<10} {'Empty':<8} {'Work Imb':<10} {'Weekend Imb':<12}")
            logging.info("─" * 90)
            
            for result in attempts_results:
                if result['success']:
                    marker = "👑" if result['attempt'] == best_attempt else "  "
                    logging.info(
                        f"{marker} {result['attempt']:<8} {result['strategy']:<25} "
                        f"{result['score']:<10.2f} {result['empty_shifts']:<8} "
                        f"{result['workload_imbalance']:<10.2f} {result['weekend_imbalance']:<12.2f}"
                    )
                else:
                    logging.info(f"  {result['attempt']:<8} {result['strategy']:<25} FAILED")
            
            # Apply the best attempt
            logging.info(f"\n🏆 Applying best attempt #{best_attempt} with score {best_score:.2f}")
            
            self.scheduler.schedule = best_schedule
            self.scheduler.worker_assignments = best_assignments
            self.scheduler.worker_shift_counts = best_counts
            self.scheduler.worker_weekend_counts = best_weekend_counts
            self.scheduler.worker_posts = best_posts
            
            # Synchronize tracking data
            self.scheduler.schedule_builder._synchronize_tracking_data()
            
            # Save as current best
            self.scheduler.schedule_builder._save_current_as_best(initial=False)
            
            logging.info("=" * 80)
            logging.info("✅ Multiple initial distribution phase completed successfully")
            logging.info("=" * 80)
            
            return True
            
        except Exception as e:
            logging.error(f"Error during multiple initial distribution attempts: {str(e)}", exc_info=True)
            return False
    
    def _iterative_improvement_phase(self, max_improvement_loops: int) -> bool:
        """
        Phase 3: Enhanced iterative improvement with smart optimization.
        
        Args:
            max_improvement_loops: Maximum number of improvement iterations
            
        Returns:
            bool: True if improvement phase completed successfully
        """
        logging.info("Phase 3: Starting enhanced iterative improvement...")
        
        # Initialize progress monitor
        self.progress_monitor = ProgressMonitor(self.scheduler, max_improvement_loops)
        self.progress_monitor.start_monitoring()
        
        improvement_loop_count = 0
        overall_improvement_made = True
        
        try:
            # Aumentar el número de ciclos por defecto si no se especifica
            if max_improvement_loops < 120:
                max_improvement_loops = 120
                
            # Calculate initial score for comparison
            current_overall_score = self.metrics.calculate_overall_schedule_score()
            logging.info(f"Score inicial: {current_overall_score:.2f}")
            
            while overall_improvement_made and improvement_loop_count < max_improvement_loops:
                loop_start_time = datetime.now()
                improvement_loop_count += 1
                
                logging.info(f"--- Starting Enhanced Improvement Loop {improvement_loop_count} ---")
                
                # Get current state for decision making
                current_state = {
                    'empty_shifts_count': self.metrics.count_empty_shifts(),
                    'workload_imbalance': self.metrics.calculate_workload_imbalance(),
                    'weekend_imbalance': self.metrics.calculate_weekend_imbalance()
                }
                
                # Get dynamically prioritized operations
                prioritized_operations = self.prioritizer.prioritize_operations_dynamically()
                
                # Execute operations with enhanced tracking
                operation_results = {}
                cycle_improvement_made = False
                
                for operation_name, operation_func, priority in prioritized_operations:
                    try:
                        # Check if operation should be skipped
                        should_skip, skip_reason = self.prioritizer.should_skip_operation(
                            operation_name, current_state
                        )
                        
                        if should_skip:
                            logging.debug(f"Skipping {operation_name}: {skip_reason}")
                            operation_results[operation_name] = {
                                'improved': False,
                                'skipped': True,
                                'reason': skip_reason
                            }
                            continue
                        
                        # Measure performance of operation
                        before_score = self.metrics.calculate_overall_schedule_score()
                        operation_start_time = datetime.now()
                        
                        # Execute operation
                        if operation_name == "synchronize_tracking_data":
                            operation_func()
                            operation_made_change = True  # This operation always "succeeds"
                        else:
                            operation_made_change = operation_func()
                        
                        operation_end_time = datetime.now()
                        execution_time = (operation_end_time - operation_start_time).total_seconds()
                        
                        # Evaluate improvement quality
                        after_score = self.metrics.calculate_overall_schedule_score()
                        
                        if operation_made_change and operation_name != "synchronize_tracking_data":
                            is_significant, improvement_ratio = self.metrics.evaluate_improvement_quality(
                                before_score, after_score, operation_name
                            )
                            
                            if is_significant:
                                logging.info(f"✅ {operation_name}: mejora significativa "
                                           f"({improvement_ratio:.4f}, +{after_score-before_score:.2f})")
                                cycle_improvement_made = True
                            else:
                                logging.debug(f"⚠️  {operation_name}: mejora marginal "
                                            f"({improvement_ratio:.4f})")
                        
                        # Record operation results
                        operation_results[operation_name] = self.prioritizer.analyze_operation_effectiveness(
                            operation_name, before_score, after_score, execution_time
                        )
                        
                    except Exception as e:
                        logging.warning(f"Operation {operation_name} failed: {str(e)}")
                        operation_results[operation_name] = {
                            'improved': False,
                            'error': str(e)
                        }
                
                # Update current score after all operations
                current_overall_score = self.metrics.calculate_overall_schedule_score()
                
                # Track iteration progress with enhanced monitoring
                progress_data = self.progress_monitor.track_iteration_progress(
                    improvement_loop_count, operation_results, current_overall_score, current_state
                )
                
                # Record iteration for trend analysis
                self.metrics.record_iteration_result(
                    improvement_loop_count, operation_results, current_overall_score
                )
                
                # Check if should continue with smart early stopping
                should_continue, reason = self.metrics.should_continue_optimization(improvement_loop_count)
                if not should_continue:
                    logging.info(f"🛑 Parada temprana activada: {reason}")
                    break
                
                # Traditional improvement check as fallback
                overall_improvement_made = cycle_improvement_made
                
                # Log cycle summary
                loop_end_time = datetime.now()
                loop_duration = (loop_end_time - loop_start_time).total_seconds()
                successful_operations = sum(
                    1 for result in operation_results.values() 
                    if isinstance(result, dict) and result.get('improved', False)
                )
                
                logging.info(f"--- Loop {improvement_loop_count} completado en {loop_duration:.2f}s. "
                           f"Operaciones exitosas: {successful_operations}/{len(operation_results)} ---")
                
                if not overall_improvement_made:
                    logging.info("No se detectaron mejoras adicionales. Finalizando fase de mejora.")

            # Final summary
            if improvement_loop_count >= max_improvement_loops:
                termination_reason = f"Límite de iteraciones alcanzado ({max_improvement_loops})"
                logging.warning(termination_reason)
            else:
                termination_reason = "Convergencia alcanzada"
                
            # Display final optimization summary
            self.progress_monitor.display_optimization_summary(
                improvement_loop_count, current_overall_score, termination_reason
            )
            
            # Get performance insights for logging
            insights = self.progress_monitor.get_performance_insights()
            if not insights.get('error'):
                logging.info(f"📊 Insights finales: {insights['significant_improvements']} mejoras significativas, "
                           f"tasa de éxito: {insights['average_operations_success_rate']:.2f}")

            return True

        except Exception as e:
            logging.error(f"Error during enhanced iterative improvement phase: {str(e)}", exc_info=True)
            return False
    
    def _finalization_phase(self) -> bool:
        """
        Phase 4: Finalize the schedule and perform final optimizations.
        
        Returns:
            bool: True if finalization was successful
        """
        logging.info("Phase 4: Finalizing schedule...")
        
        try:
            # Final adjustment of last post distribution
            logging.info("Performing final last post distribution adjustment...")
            max_iterations = self.config.get('last_post_adjustment_max_iterations', 
                                           SchedulerConfig.DEFAULT_LAST_POST_ADJUSTMENT_ITERATIONS)

            if self.scheduler.schedule_builder._adjust_last_post_distribution(
                balance_tolerance=1.0,
                max_iterations=max_iterations
            ):
                logging.info("Final last post distribution adjustment completed.")


            # PASADA EXTRA: Llenar huecos y balancear tras el ajuste final
            logging.info("Extra pass: Filling empty shifts and balancing workloads after last post adjustment...")
            self.scheduler.schedule_builder._try_fill_empty_shifts()
            self.scheduler.schedule_builder._balance_workloads()
            self.scheduler.schedule_builder._balance_weekday_distribution()

            # Iterar hasta que todos los trabajadores estén dentro de la tolerancia ±1 en turnos y last posts
            max_final_balance_loops = 50
            for i in range(max_final_balance_loops):
                logging.info(f"Final strict balance loop {i+1}/{max_final_balance_loops}")
                changed1 = self.scheduler.schedule_builder._balance_workloads()
                changed2 = self.scheduler.schedule_builder._adjust_last_post_distribution(balance_tolerance=1.0, max_iterations=10)
                changed3 = self.scheduler.schedule_builder._balance_weekday_distribution()
                if not changed1 and not changed2 and not changed3:
                    logging.info(f"Balance achieved after {i+1} iterations")
                    break
            else:
                logging.warning(f"Max balance iterations ({max_final_balance_loops}) reached")

            # Get the best schedule
            final_schedule_data = self.scheduler.schedule_builder.get_best_schedule()

            if not final_schedule_data or not final_schedule_data.get('schedule'):
                logging.error("No best schedule data available for finalization.")
                return self._handle_fallback_finalization()

            # Update scheduler state with final schedule
            self._apply_final_schedule(final_schedule_data)

            # Final validation y logging
            self._perform_final_validation()

            logging.info("Schedule finalization phase completed successfully.")
            return True

        except Exception as e:
            logging.error(f"Error during finalization phase: {str(e)}", exc_info=True)
            return False
    
    def _handle_fallback_finalization(self) -> bool:
        """
        Handle fallback finalization when no best schedule is available.
        
        Returns:
            bool: True if fallback was successful
        """
        logging.warning("Using current schedule state as fallback for finalization.")
        
        if not self.scheduler.schedule or all(all(p is None for p in posts) for posts in self.scheduler.schedule.values()):
            logging.error("Current schedule state is also empty. Cannot finalize.")
            return False
        
        # Use current state as final schedule
        final_schedule_data = {
            'schedule': self.scheduler.schedule,
            'worker_assignments': self.scheduler.worker_assignments,
            'worker_shift_counts': self.scheduler.worker_shift_counts,
            'worker_weekend_counts': self.scheduler.worker_weekend_counts,
            'worker_posts': self.scheduler.worker_posts,
            'last_assignment_date': self.scheduler.last_assignment_date,
            'consecutive_shifts': self.scheduler.consecutive_shifts,
            'score': self.scheduler.calculate_score()
        }
        
        return self._apply_final_schedule(final_schedule_data)
    
    def _apply_final_schedule(self, final_schedule_data: Dict[str, Any]) -> bool:
        """
        Apply the final schedule data to the scheduler state.
        
        Args:
            final_schedule_data: Dictionary containing the final schedule data
            
        Returns:
            bool: True if application was successful
        """
        try:
            logging.info("Applying final schedule data to scheduler state...")
            
            self.scheduler.schedule = final_schedule_data['schedule']
            self.scheduler.worker_assignments = final_schedule_data['worker_assignments']
            self.scheduler.worker_shift_counts = final_schedule_data['worker_shift_counts']
            self.scheduler.worker_weekend_counts = final_schedule_data.get(
                'worker_weekend_shifts', 
                final_schedule_data.get('worker_weekend_counts', {})
            )
            self.scheduler.worker_posts = final_schedule_data['worker_posts']
            self.scheduler.last_assignment_date = final_schedule_data['last_assignment_date']
            self.scheduler.consecutive_shifts = final_schedule_data['consecutive_shifts']
            
            final_score = final_schedule_data.get('score', float('-inf'))
            logging.info(f"Final schedule applied with score: {final_score:.2f}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error applying final schedule data: {str(e)}", exc_info=True)
            return False
    
    def _perform_final_validation(self) -> bool:
        """
        Perform final validation and logging of the schedule.
        
        Returns:
            bool: True if validation passed
        """
        try:
            # Calculate final statistics
            total_slots_final = sum(len(slots) for slots in self.scheduler.schedule.values())
            total_assignments_final = sum(
                1 for slots in self.scheduler.schedule.values() 
                for worker_id in slots if worker_id is not None
            )
            
            empty_shifts_final = [
                (date, post_idx) 
                for date, posts in self.scheduler.schedule.items() 
                for post_idx, worker_id in enumerate(posts) 
                if worker_id is None
            ]
            
            # Validate schedule integrity
            if total_slots_final == 0:
                schedule_duration_days = (self.end_date - self.start_date).days + 1
                if schedule_duration_days > 0:
                    logging.error(f"Final schedule has 0 total slots despite valid date range ({schedule_duration_days} days).")
                    return False
            
            if total_assignments_final == 0 and total_slots_final > 0:
                logging.warning(f"Final schedule has {total_slots_final} slots but contains ZERO assignments.")
            
            if empty_shifts_final:
                empty_percentage = (len(empty_shifts_final) / total_slots_final) * 100
                logging.warning(f"Final schedule has {len(empty_shifts_final)} empty shifts ({empty_percentage:.1f}%) out of {total_slots_final} total slots.")
            
            # Log final summary
            self.scheduler.log_schedule_summary("Final Generated Schedule")
            
            # Apply iterative tolerance optimization to meet ±8% requirements
            logging.info("=" * 80)
            logging.info("APPLYING ITERATIVE TOLERANCE OPTIMIZATION")
            logging.info("=" * 80)
            self._apply_tolerance_optimization()
            
            return True
            
        except Exception as e:
            logging.error(f"Error during final validation: {str(e)}", exc_info=True)
            return False
    
    def _apply_tolerance_optimization(self):
        """
        Apply iterative optimization to meet ±8% tolerance requirements.
        
        This method uses the IterativeOptimizer to automatically correct tolerance violations
        by redistributing shifts between workers who are over/under their target allocations.
        """
        try:
            # Check initial tolerance violations
            outside_general = self.tolerance_validator.get_workers_outside_tolerance(
                is_weekend_only=False
            )
            outside_weekend = self.tolerance_validator.get_workers_outside_tolerance(
                is_weekend_only=True
            )
            
            total_violations = len(outside_general) + len(outside_weekend)
            
            logging.info(f"Initial tolerance check:")
            logging.info(f"  Workers outside ±8% tolerance (general): {len(outside_general)}")
            logging.info(f"  Workers outside ±8% tolerance (weekend): {len(outside_weekend)}")
            logging.info(f"  Total violations: {total_violations}")
            
            if total_violations == 0:
                logging.info("✅ All workers already within ±8% tolerance!")
                return
            
            # Log violations details
            if outside_general:
                logging.info("General shift violations:")
                for violation in outside_general[:5]:  # Show first 5
                    logging.info(f"  - {violation['worker_id']}: {violation['assigned_shifts']} assigned "
                               f"(target: {violation['target_shifts']}, "
                               f"deviation: {violation['deviation_percentage']:+.1f}%)")
            
            if outside_weekend:
                logging.info("Weekend shift violations:")
                for violation in outside_weekend[:5]:  # Show first 5
                    logging.info(f"  - {violation['worker_id']}: {violation['assigned_shifts']} assigned "
                               f"(target: {violation['target_shifts']}, "
                               f"deviation: {violation['deviation_percentage']:+.1f}%)")
            
            # Apply iterative optimization
            logging.info(f"Starting iterative optimization (max {self.iterative_optimizer.max_iterations} iterations)...")
            
            optimized_schedule = self.iterative_optimizer.optimize(
                schedule=self.scheduler.schedule,
                workers_data=self.workers_data,
                schedule_config=self.config,
                scheduler_core=self
            )
            
            # Check if optimization improved the schedule
            if optimized_schedule and optimized_schedule != self.scheduler.schedule:
                # Apply optimized schedule temporarily to check
                original_schedule = self.scheduler.schedule
                self.scheduler.schedule = optimized_schedule
                
                # Verify improved tolerance
                new_outside_general = self.tolerance_validator.get_workers_outside_tolerance(
                    is_weekend_only=False
                )
                new_outside_weekend = self.tolerance_validator.get_workers_outside_tolerance(
                    is_weekend_only=True
                )
                
                new_total_violations = len(new_outside_general) + len(new_outside_weekend)
                
                if new_total_violations < total_violations:
                    logging.info(f"✅ Optimization successful! Violations reduced: {total_violations} → {new_total_violations}")
                    logging.info(f"  General violations: {len(outside_general)} → {len(new_outside_general)}")
                    logging.info(f"  Weekend violations: {len(outside_weekend)} → {len(new_outside_weekend)}")
                    
                    # Keep optimized schedule (already applied)
                    # Resync tracking data
                    self.scheduler._synchronize_tracking_data()
                    
                    logging.info("Optimized schedule applied successfully")
                elif new_total_violations == total_violations:
                    logging.info(f"Optimization did not reduce violations (still {total_violations})")
                    logging.info("Keeping original schedule")
                    self.scheduler.schedule = original_schedule
                else:
                    logging.warning(f"Optimization made things worse: {total_violations} → {new_total_violations}")
                    logging.info("Keeping original schedule")
                    self.scheduler.schedule = original_schedule
            else:
                logging.info("No optimization improvements found, keeping original schedule")
            
            # Final tolerance report
            final_outside_general = self.tolerance_validator.get_workers_outside_tolerance(
                is_weekend_only=False
            )
            final_outside_weekend = self.tolerance_validator.get_workers_outside_tolerance(
                is_weekend_only=True
            )
            
            final_total = len(final_outside_general) + len(final_outside_weekend)
            
            logging.info("=" * 80)
            logging.info("TOLERANCE OPTIMIZATION COMPLETE")
            logging.info(f"Final violations: {final_total}")
            logging.info(f"  General: {len(final_outside_general)}")
            logging.info(f"  Weekend: {len(final_outside_weekend)}")
            
            if final_total == 0:
                logging.info("🎯 SUCCESS: All workers within ±8% tolerance!")
            else:
                logging.warning(f"⚠️  {final_total} workers still outside tolerance")
            logging.info("=" * 80)
            
        except Exception as e:
            logging.error(f"Error during tolerance optimization: {e}", exc_info=True)
            logging.info("Continuing with original schedule")
    
    def _select_distribution_strategy(self, attempt_num: int, total_attempts: int) -> Dict[str, Any]:
        """
        Select a distribution strategy for this attempt.
        
        Different strategies vary in:
        - Worker ordering (random, balanced, sequential)
        - Random seed
        - Priority criteria
        
        Args:
            attempt_num: Current attempt number (1-indexed)
            total_attempts: Total number of attempts
            
        Returns:
            Dict with strategy configuration
        """
        strategies = [
            {
                'name': 'Balanced Sequential',
                'worker_order': 'balanced',
                'randomize': False,
                'seed': None,
                'description': 'Workers ordered by workload balance, deterministic assignment'
            },
            {
                'name': 'Random Seed A',
                'worker_order': 'random',
                'randomize': True,
                'seed': 42 + attempt_num,
                'description': 'Random worker order with specific seed for reproducibility'
            },
            {
                'name': 'Sequential by ID',
                'worker_order': 'sequential',
                'randomize': False,
                'seed': None,
                'description': 'Workers processed in ID order, deterministic'
            },
            {
                'name': 'Random Seed B',
                'worker_order': 'random',
                'randomize': True,
                'seed': 100 + attempt_num * 7,
                'description': 'Different random seed for variation'
            },
            {
                'name': 'Reverse Sequential',
                'worker_order': 'reverse',
                'randomize': False,
                'seed': None,
                'description': 'Workers processed in reverse ID order'
            },
            {
                'name': 'Random Seed C',
                'worker_order': 'random',
                'randomize': True,
                'seed': 200 + attempt_num * 13,
                'description': 'Another random variation'
            },
            {
                'name': 'Workload Priority',
                'worker_order': 'workload',
                'randomize': False,
                'seed': None,
                'description': 'Prioritize workers with fewer assignments'
            },
            {
                'name': 'Random Seed D',
                'worker_order': 'random',
                'randomize': True,
                'seed': 300 + attempt_num * 17,
                'description': 'Yet another random variation'
            },
            {
                'name': 'Alternating Pattern',
                'worker_order': 'alternating',
                'randomize': False,
                'seed': None,
                'description': 'Alternate between high and low workload workers'
            },
            {
                'name': 'Random Seed E',
                'worker_order': 'random',
                'randomize': True,
                'seed': 400 + attempt_num * 23,
                'description': 'Final random variation'
            }
        ]
        
        # Select strategy based on attempt number
        strategy_index = (attempt_num - 1) % len(strategies)
        return strategies[strategy_index]
    
    def _perform_initial_fill_with_strategy(self, strategy: Dict[str, Any]) -> bool:
        """
        Perform initial schedule fill using the specified strategy.
        
        Args:
            strategy: Strategy configuration dictionary
            
        Returns:
            bool: True if fill was successful
        """
        try:
            # Set random seed if specified
            if strategy.get('seed') is not None:
                random.seed(strategy['seed'])
            
            # Get worker list based on strategy
            workers_list = self._get_ordered_workers_list(strategy['worker_order'])
            
            logging.info(f"Filling schedule with {len(workers_list)} workers using '{strategy['name']}' strategy")
            
            # Perform initial fill
            # Use adaptive iteration config to determine fill attempts
            adaptive_config = self.adaptive_manager.calculate_adaptive_iterations()
            fill_attempts = adaptive_config.get('fill_attempts', 16)
            
            logging.info(f"Using {fill_attempts} fill attempts based on adaptive configuration")
            
            # Call schedule builder's fill method with custom worker ordering
            success = self.scheduler.schedule_builder._try_fill_empty_shifts_with_worker_order(
                workers_list, max_attempts=fill_attempts
            )
            
            if success:
                logging.info(f"✅ Initial fill successful with '{strategy['name']}' strategy")
            else:
                logging.warning(f"⚠️  Initial fill had issues with '{strategy['name']}' strategy")
            
            return success
            
        except AttributeError:
            # Fallback if custom worker order method doesn't exist
            logging.warning("Custom worker order method not available, using standard fill")
            return self.scheduler.schedule_builder._try_fill_empty_shifts()
            
        except Exception as e:
            logging.error(f"Error during initial fill with strategy '{strategy['name']}': {e}", exc_info=True)
            return False
    
    def _get_ordered_workers_list(self, order_type: str) -> List[Dict]:
        """
        Get workers list ordered according to specified type.
        
        Args:
            order_type: Type of ordering ('balanced', 'random', 'sequential', 'reverse', 
                       'workload', 'alternating')
            
        Returns:
            List of worker dictionaries in specified order
        """
        workers = list(self.workers_data)
        
        if order_type == 'random':
            random.shuffle(workers)
            
        elif order_type == 'sequential':
            workers.sort(key=lambda w: w['id'])
            
        elif order_type == 'reverse':
            workers.sort(key=lambda w: w['id'], reverse=True)
            
        elif order_type == 'balanced':
            # Order by current assignment count (fewer first)
            workers.sort(key=lambda w: self.scheduler.worker_shift_counts.get(w['id'], 0))
            
        elif order_type == 'workload':
            # Order by target shifts (higher target first)
            workers.sort(key=lambda w: w.get('target_shifts', 0), reverse=True)
            
        elif order_type == 'alternating':
            # Alternate between low and high workload
            workers.sort(key=lambda w: self.scheduler.worker_shift_counts.get(w['id'], 0))
            alternated = []
            low_idx = 0
            high_idx = len(workers) - 1
            while low_idx <= high_idx:
                if low_idx == high_idx:
                    alternated.append(workers[low_idx])
                else:
                    alternated.append(workers[low_idx])
                    alternated.append(workers[high_idx])
                low_idx += 1
                high_idx -= 1
            workers = alternated
        
        return workers