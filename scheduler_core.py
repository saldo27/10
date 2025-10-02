"""
Scheduler Core Module

This module contains the main orchestration logic for the scheduler system,
extracted from the original Scheduler class to improve maintainability and separation of concerns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple, Any

from scheduler_config import SchedulerConfig
from exceptions import SchedulerError
from optimization_metrics import OptimizationMetrics
from operation_prioritizer import OperationPrioritizer
from progress_monitor import ProgressMonitor
from iterative_optimizer import IterativeOptimizer
from shift_tolerance_validator import ShiftToleranceValidator


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
        self.iterative_optimizer = IterativeOptimizer(max_iterations=20, tolerance=0.08)  # Increased iterations and tolerance
        
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
            
            # Update dynamic priorities after mandatory assignment
            self.scheduler.schedule_builder.update_dynamic_priorities()
            
            # Save initial state as best
            self.scheduler.schedule_builder._save_current_as_best(initial=True)
            
            # Log summary
            self.scheduler.log_schedule_summary("After Mandatory Assignment")
            
            logging.info("Mandatory assignment phase completed")
            return True
            
        except Exception as e:
            logging.error(f"Failed in mandatory assignment phase: {str(e)}", exc_info=True)
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
                
                # Update dynamic priorities at the start of each improvement iteration
                if improvement_loop_count % 5 == 1:  # Update every 5 iterations to balance performance
                    self.scheduler.schedule_builder.update_dynamic_priorities()
                
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
            # Update dynamic priorities one final time before finalization
            self.scheduler.schedule_builder.update_dynamic_priorities()
            
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
            
            # Perform tolerance validation for +/-9% requirement
            logging.info("Performing shift tolerance validation (+/-9%)...")
            self.scheduler.tolerance_validator.log_tolerance_report()
            
            # Check if any workers are significantly outside tolerance
            outside_tolerance_general = self.scheduler.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=False)
            outside_tolerance_weekend = self.scheduler.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=True)
            
            if outside_tolerance_general:
                logging.warning(f"{len(outside_tolerance_general)} workers are outside +/-9% tolerance for general shifts")
                for worker_info in outside_tolerance_general:
                    if abs(worker_info['deviation_percentage']) > 10:  # Flag significant deviations
                        logging.error(f"Worker {worker_info['worker_id']} has significant deviation: {worker_info['deviation_percentage']:.1f}%")
            
            if outside_tolerance_weekend:
                logging.warning(f"{len(outside_tolerance_weekend)} workers are outside +/-9% tolerance for weekend shifts")
                for worker_info in outside_tolerance_weekend:
                    if abs(worker_info['deviation_percentage']) > 10:  # Flag significant deviations
                        logging.error(f"Worker {worker_info['worker_id']} has significant weekend deviation: {worker_info['deviation_percentage']:.1f}%")
            
            # APPLY TOLERANCE OPTIMIZATION IF VIOLATIONS DETECTED
            total_violations = len(outside_tolerance_general) + len(outside_tolerance_weekend)
            if total_violations > 0:
                logging.info(f"🔍 Detected {total_violations} tolerance violations - starting iterative optimization...")
                
                # Store original violations for comparison
                original_general = len(outside_tolerance_general)
                original_weekend = len(outside_tolerance_weekend)
                original_violations = original_general + original_weekend
                
                try:
                    success = self._apply_tolerance_optimization()
                    
                    if success:
                        logging.info("✅ All tolerance requirements satisfied after optimization!")
                    else:
                        logging.warning("⚠️  Some tolerance violations remain after optimization")
                except Exception as e:
                    logging.error(f"❌ Error during tolerance optimization: {e}", exc_info=True)
                    success = False
                    
                # Re-validate after optimization to show improvement
                post_opt_general = self.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=False)
                post_opt_weekend = self.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=True)
                final_violations = len(post_opt_general) + len(post_opt_weekend)
                
                if final_violations < original_violations:
                    logging.info(f"📈 Optimization improved violations from {original_violations} to {final_violations}")
                elif final_violations == 0:
                    logging.info("✅ All tolerance violations resolved!")
                else:
                    logging.warning(f"⚠️  {final_violations} violations remain after optimization")
                    
            else:
                logging.info("✅ All workers already within ±8% tolerance!")
            
            # Log final summary
            self.scheduler.log_schedule_summary("Final Generated Schedule")
            
            return True
            
        except Exception as e:
            logging.error(f"Error during final validation: {str(e)}", exc_info=True)
            return False
    
    def _apply_tolerance_optimization(self) -> bool:
        """
        Apply iterative optimization to meet ±8% tolerance requirements.
        
        Returns:
            bool: True if all tolerance requirements are satisfied
        """
        logging.info("🔄 Starting tolerance optimization with iterative refinement...")
        logging.info("=" * 60)
        logging.info("TOLERANCE OPTIMIZATION STARTING - THIS MESSAGE SHOULD BE VISIBLE")
        logging.info("=" * 60)
        
        try:
            # Get current schedule data
            schedule_config = {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'num_shifts': self.config.get('num_shifts', 3),
                'holidays': self.config.get('holidays', [])
            }
            
            logging.info(f"Debug: Schedule config prepared - dates: {self.start_date} to {self.end_date}")
            logging.info(f"Debug: About to call iterative optimizer with {len(self.scheduler.schedule)} schedule entries")
            
            # Run iterative optimization
            result = self.iterative_optimizer.optimize_schedule(
                scheduler_core=self,
                schedule=self.scheduler.schedule,
                workers_data=self.workers_data,
                schedule_config=schedule_config
            )
            
            logging.info(f"Debug: Optimization result - success: {result.success}, violations: {result.total_violations}")
            
            # Update schedule if optimization was successful or shows improvement
            should_apply = False
            reason = ""
            
            if result.schedule:
                if result.total_violations == 0:
                    should_apply = True
                    reason = "all violations resolved"
                elif result.total_violations < 15:  # Accept reasonable results
                    should_apply = True
                    reason = f"violations reduced to acceptable level ({result.total_violations})"
                elif hasattr(result, 'initial_violations') and result.total_violations < result.initial_violations * 0.7:
                    should_apply = True
                    reason = f"significant improvement (30%+ reduction)"
                else:
                    reason = f"insufficient improvement - violations: {result.total_violations}"
            else:
                reason = "no optimized schedule returned"
            
            if should_apply:
                logging.info(f"📈 Applying optimized schedule - {reason}")
                
                # Debug: Log schedule format and size before applying
                original_schedule_size = len(str(self.scheduler.schedule))
                optimized_schedule_size = len(str(result.schedule))
                original_shifts = sum(1 for date_data in self.scheduler.schedule.values() for worker in date_data if worker is not None)
                
                logging.info(f"Debug: Original schedule - size: {original_schedule_size}, shifts: {original_shifts}")
                logging.info(f"Debug: Optimized schedule - size: {optimized_schedule_size}")
                logging.info(f"Debug: Optimized schedule type: {type(result.schedule)}")
                logging.info(f"Debug: First few optimized entries: {str(result.schedule)[:200]}...")
                
                self.scheduler.schedule = result.schedule
                
                # Resynchronize tracking data
                self.scheduler.schedule_builder._synchronize_tracking_data()
            else:
                logging.warning(f"⚠️  Not applying optimized schedule - {reason}")
                
            # Log optimization summary
            summary = self.iterative_optimizer.get_optimization_summary()
            if summary.get('total_iterations', 0) > 0:
                logging.info(f"📊 Optimization Summary:")
                logging.info(f"   Iterations: {summary['total_iterations']}")
                logging.info(f"   Initial violations: {summary['initial_violations']}")
                logging.info(f"   Final violations: {summary['final_violations']}")
                logging.info(f"   Total improvement: {summary['improvement']}")
                logging.info(f"   Average improvement rate: {summary['average_improvement_rate']:.2f}")
                logging.info(f"   Convergence: {'Yes' if summary['convergence_achieved'] else 'No'}")
                
                if summary['stagnation_counter'] > 0:
                    logging.info(f"   Final stagnation: {summary['stagnation_counter']} iterations")
            
            # Final tolerance validation using existing methods
            original_schedule = self.tolerance_validator.schedule
            self.tolerance_validator.schedule = self.scheduler.schedule
            
            # Get violation counts
            general_outside = self.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=False)
            weekend_outside = self.tolerance_validator.get_workers_outside_tolerance(is_weekend_only=True)
            
            general_violations = len(general_outside)
            weekend_violations = len(weekend_outside)
            total_violations = general_violations + weekend_violations
            
            # Restore original schedule reference
            self.tolerance_validator.schedule = original_schedule
            
            # Log validation results
            if total_violations == 0:
                logging.info("✅ ALL TOLERANCE REQUIREMENTS SATISFIED!")
                return True
            else:
                logging.warning(f"⚠️  {total_violations} tolerance violations remain after optimization")
                logging.info("📋 Remaining violations summary:")
                
                # Log specific remaining violations
                if general_violations > 0:
                    logging.warning(f"   General shift violations: {general_violations}")
                    for worker_info in general_outside:
                        if abs(worker_info.get('deviation_percentage', 0)) > 10:
                            logging.error(f"   Worker {worker_info.get('worker_id', 'Unknown')} deviation: {worker_info.get('deviation_percentage', 0):.1f}%")
                
                if weekend_violations > 0:
                    logging.warning(f"   Weekend shift violations: {weekend_violations}")
                    for worker_info in weekend_outside:
                        if abs(worker_info.get('deviation_percentage', 0)) > 10:
                            logging.error(f"   Worker {worker_info.get('worker_id', 'Unknown')} weekend deviation: {worker_info.get('deviation_percentage', 0):.1f}%")
                
                return False
        
        except Exception as e:
            logging.error(f"Error during tolerance optimization: {str(e)}", exc_info=True)
            # Return False but don't crash - continue with original schedule
            return False