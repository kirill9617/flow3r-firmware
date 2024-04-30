#include "tuner.h"
#include <stdlib.h>
#include <esp_log.h>
#define TAG "Tuner"
radspa_t * tuner_create(uint32_t);
void tuner_destroy(radspa_t * plugin);
radspa_descriptor_t tuner_desc = {
    .name = "tuner",
    .id = 1549,
    .description = "TODO",
    .create_plugin_instance = tuner_create,
    .destroy_plugin_instance = tuner_destroy,
};

#define TUNER_INPUT 0
#define TUNER_OUTPUT 1
#define TUNER_PITCH 2
#define TUNER_MAX 3
#define TUNER_LINE 4

#define TUNER_NUM_SIGNALS 5

#define LINE(plugin) radspa_signal_set_const_value(radspa_signal_get_by_index(plugin, TUNER_LINE),__LINE__);


radspa_t * tuner_create(uint32_t init_var){
    if(init_var == 0) init_var = 64;
        ESP_LOGE(TAG, "tuner_create %d %lu",__LINE__,init_var);
    // if(init_var > 10000) init_var = 10000;
    uint32_t buffer_size = init_var;//*(48000/1000);
        ESP_LOGE(TAG, "tuner_create %d %lu",__LINE__,buffer_size);
    radspa_t * tuner = radspa_standard_plugin_create(&tuner_desc, TUNER_NUM_SIGNALS, sizeof(tuner_data_t), buffer_size);
    if(tuner == NULL) return NULL;
    tuner->render = tuner_run;
    radspa_signal_set(tuner, TUNER_PITCH, "pitch", RADSPA_SIGNAL_HINT_OUTPUT, 0);
    tuner_data_t * plugin_data = tuner->plugin_data;
    plugin_data->first_run = true;
    plugin_data->buffer_size=buffer_size;
    plugin_data->buffer_count=0;
    
    // plugin_data->time_prev = -1;
    // plugin_data->max_delay = init_var;
    radspa_signal_set(tuner, TUNER_OUTPUT, "output", RADSPA_SIGNAL_HINT_OUTPUT, 0);
    radspa_signal_set(tuner, TUNER_INPUT, "input", RADSPA_SIGNAL_HINT_INPUT, 0);
    radspa_signal_set(tuner, TUNER_MAX, "max", RADSPA_SIGNAL_HINT_OUTPUT, 0);
    radspa_signal_set(tuner, TUNER_LINE, "line", RADSPA_SIGNAL_HINT_OUTPUT, 0);
    // radspa_signal_set(delay, DELAY_TIME, "time", RADSPA_SIGNAL_HINT_INPUT, 200);
    // radspa_signal_set(delay, DELAY_FEEDBACK, "feedback", RADSPA_SIGNAL_HINT_INPUT, 16000);
    // radspa_signal_set(delay, DELAY_LEVEL, "level", RADSPA_SIGNAL_HINT_INPUT, 16000);
    // radspa_signal_set(delay, DELAY_DRY_VOL, "dry_vol", RADSPA_SIGNAL_HINT_INPUT, 32767);
    // radspa_signal_set(delay, DELAY_REC_VOL, "rec_vol", RADSPA_SIGNAL_HINT_INPUT, 32767);

        ESP_LOGE(TAG, "tuner_create %d",__LINE__);

   /* init data structures */
   plugin_data->data_buf = (double *) malloc( sizeof(double) * ( buffer_size ) );
   plugin_data->maxs = (double *) malloc( sizeof(double) * ( buffer_size/2 ) );
   plugin_data->mins = (double *) malloc( sizeof(double) * (buffer_size/2 ) );
   plugin_data->distances = (int *) malloc( sizeof(int) * (buffer_size/2 ) );

        ESP_LOGE(TAG, "tuner_create %d",__LINE__);
        LINE(tuner);
    return tuner;
}


void tuner_destroy(radspa_t * tuner){
    tuner_data_t * plugin_data = tuner->plugin_data;
   if (plugin_data->data_buf){free(plugin_data->data_buf);}
   if (plugin_data->maxs){free(plugin_data->maxs);}
   if (plugin_data->mins){free(plugin_data->mins);}
   if (plugin_data->distances){free(plugin_data->distances);}
   radspa_standard_plugin_destroy(tuner);
}

static double __compute_pitch(radspa_t* tuner){
   tuner_data_t * plugin_data = tuner->plugin_data;
   double *approx = plugin_data->data_buf;
   unsigned int samplecount = plugin_data->buffer_count;
unsigned int sample_format = S16;
double pitch = UNPITCHED, mean=0.0, max_freq, max_threshold_ratio, mode=0.0, old_mode_value=0.;
   double max_threshold, min_threshold, DC_component = 0., max_value = 0. ,min_value = 0. , mean_no=0;
   double *mins = plugin_data->mins;
   double *maxs = plugin_data->maxs;
   int *distances = plugin_data->distances;
   int dist_delta;
   unsigned int curr_sample_number = samplecount, curr_level;
   unsigned int max_flwt_levels, diff_levels, power2 = 1;//power2 is just to calculate powers of 2 as to speed evertything up
   unsigned int d_index, max_d_index;
   register unsigned int count, center_mode_i, center_mode_c; // centermode index and centermode count
   register unsigned int mins_no, maxs_no, zero_crossed;
   register int too_close, sign_test, prev_sign_test= 0, j, i;
   static double last_mode = UNPITCHED;
   static int last_iter = NONE;

   //Algorithm parameters
   max_flwt_levels = FLWT_LEVELS;//settings->flwt_levels;
   max_freq = MAX_FREQ;//settings->max_freq;
   diff_levels = DIFFS_LEVELS;//settings->diff_levels;
   max_threshold_ratio = THRESHOLD_RATIO;//settings->max_threshold_ratio;

   /* compute amplitude Threshold and the DC component */
   LINE(tuner);
   for( i = 0 ; i< samplecount ; i++){
      DC_component += approx[i];

      max_value = max( approx[i], max_value );
      min_value = min( approx[i], min_value );
   }


   //as to distinguish silence
   if( sample_format && max_value < sample_format ){
      LINE(tuner);
      last_mode = UNPITCHED;
      last_iter = NONE;
      return UNPITCHED;
   }

   DC_component = DC_component/samplecount;
   max_threshold = (max_value - DC_component)*max_threshold_ratio + DC_component;
   min_threshold = (min_value - DC_component)*max_threshold_ratio + DC_component;


   for( curr_level=1; curr_level < max_flwt_levels ; curr_level++ ){

      /* set data as to compute the FLWT */
      mins_no = 0;
      maxs_no = 0;
      power2<<=1;

      /* perform the FLWT */
      curr_sample_number /= 2;
      for(j=0; j<=curr_sample_number ; j++){
         approx[j] = ( approx[2*j] + approx[2*j + 1] )/2;
      }

      /*now store the first maxima and minima after each zero-crossing, only store them if they respect the delta rule (above)
        and are greater than the minimum threshold ( amplitude_threshold) */
      dist_delta = (int) max( floor( SAMPLE_RATE/ ( max_freq * power2 ) ), 1);

      //checks if the wave is going up or down, =1 if positive, =-1 if negative
      if( approx[1] - approx[0] > 0 )
         prev_sign_test = 1;
      else
         prev_sign_test = -1;

      zero_crossed = 1; //zero crossing test
      too_close = 0; // keep tracks of how many samples must not be taken into considerations ( max/min finding ) because of the delta

      for( j=1 ; j< curr_sample_number ; j++ ){
         sign_test = approx[j] - approx[j-1];

         if( prev_sign_test >= 0 && sign_test < 0 ){
            if( approx[j-1] >= max_threshold && zero_crossed && !too_close){
               maxs[maxs_no] = j-1;
               maxs_no++;
               zero_crossed = 0;
               too_close = dist_delta;
            }
         }
         else if( prev_sign_test <=0 && sign_test>0 ){
            if( approx[j-1] <= min_threshold && zero_crossed && !too_close ){
               mins[mins_no] = j-1;
               mins_no++;
               zero_crossed = 0;
               too_close = dist_delta;
            }
         }

         if( ( approx[j] <= DC_component && approx[j-1] > DC_component ) || ( approx[j] >= DC_component && approx[j-1] < DC_component ) )
            zero_crossed = 1;

         prev_sign_test = sign_test;

         if(too_close)
            too_close--;

      }

      /* determine the mode distance between the maxima/minima */
      if( maxs_no ||  mins_no ){

         memset( distances, 0, sizeof(int) * curr_sample_number );

         max_d_index = 0; //useful for keeping track of the maximum used index of the array
         d_index = 0;

         for( j=0; j< maxs_no ; j++)
            for( i=1 ; i<= diff_levels ; i++ )
               if( i+j < maxs_no ){
                  d_index = abs_val( maxs[j] - maxs[i+j] );
                  distances[d_index]++;
                  if( d_index > max_d_index )
                     max_d_index = d_index;
               }

         for( j=0; j< mins_no ; j++)
            for( i=1 ; i<= diff_levels ; i++ )
               if( i+j < mins_no ){
                  d_index = abs_val( mins[j] - mins[i+j] );
                  distances[d_index]++;
                  if( d_index > max_d_index )
                     max_d_index = d_index;
               }

         center_mode_c = 1;
         center_mode_i = 0;

         /* select center mode */
         for( i = 0 ; i <= max_d_index ; i++ ){

            if( distances[i] == 0 ) //useless to go on if this distance is not part of the set of real calculated distances
               continue;

            count = 0;

            for( j = -dist_delta ; j <= dist_delta ; j++){
               if( i+j >= 0 && i+j <= max_d_index )
                  count += distances[i+j];
            }

            if( count == center_mode_c && count > floor(curr_sample_number/i/4) ){
               if( last_mode != UNPITCHED && abs_val( i - last_mode/power2 ) <= dist_delta ){
                  center_mode_i = i;
               }
               else if( i== center_mode_i*2 ){
                  center_mode_i = i;
               }

            }
            else if( count > center_mode_c ){
               center_mode_i = i;
               center_mode_c = count;
            }
            else if( count == center_mode_c-1 && last_mode > UNPITCHED && abs_val( i - last_mode/power2 ) <= dist_delta )
               center_mode_i = i;

         }

         /* mode averaging*/
         mean_no = 0;
         mean = 0;

         if( center_mode_i > 0 ){
            for( i= -dist_delta ; i <= dist_delta ; i++){
               if( center_mode_i + i >= 0 && center_mode_i + i <= max_d_index ){
                  if( distances[center_mode_i+i] == 0 )
                     continue;

                  mean_no += distances[center_mode_i+i];
                  mean += (center_mode_i+i) * distances[center_mode_i+i];
               }

            }
            mode = mean / mean_no;
         }
      }else if( maxs_no == 0 && mins_no == 0){
        LINE(tuner);
         // free(maxs);
         // free(mins);
         // free(distances);
         last_mode = UNPITCHED;
         last_iter = NONE;
         return UNPITCHED;
      }

      /* letś see if we can see some underlying periodicity */


      /* if the mode distance is equivalent to that of the previous level, then is taken as the period, otherwise next level of FLWT */
       if( old_mode_value>0.  && abs_val( 2*mode - old_mode_value ) <= dist_delta  ){
        LINE(tuner);
         // free(maxs);
         // free(mins);
         // free(distances);

         pitch = SAMPLE_RATE/( power2/2*old_mode_value );
         last_iter = curr_level-2;
         last_mode = mode;
         return pitch;
       }
       /* if the mode from the previous windows is similar to the one computed in the current window, then it is the same frequency */
       else if( last_mode > 0. && curr_level == 1 && last_iter>-1 && ( abs_val( ( last_mode*( power2<<last_iter)) - mode ) ) <= dist_delta ){
        LINE(tuner);
          // free(maxs);
          // free(mins);
          // free(distances);

          pitch = SAMPLE_RATE/( power2*mode );
          last_mode = mode;
          last_iter = 1;
          return pitch;
       }

       /*set oldmode for next iteration*/
       old_mode_value = mode;
   }

        LINE(tuner);
   // No pitch detected
   // free(maxs);
   // free(mins);
   // free(distances);
   last_mode = UNPITCHED;
   last_iter = NONE;
   return UNPITCHED;
}

void tuner_run(radspa_t * tuner, uint16_t num_samples, uint32_t render_pass_id){
// ESP_LOGE(TAG,"tuner_run");
    radspa_signal_t * input_sig = radspa_signal_get_by_index(tuner, TUNER_INPUT);
    radspa_signal_t * output_sig = radspa_signal_get_by_index(tuner, TUNER_OUTPUT);
    radspa_signal_t * pitch_sig = radspa_signal_get_by_index(tuner, TUNER_PITCH);
    radspa_signal_t * max_sig = radspa_signal_get_by_index(tuner, TUNER_MAX);
    tuner_data_t * plugin_data = tuner->plugin_data;
    

   int16_t max = 0;
   

   for (uint16_t i=0;i<num_samples;i++){
	int16_t val = radspa_signal_get_value(input_sig,i,render_pass_id);
	radspa_signal_set_value(output_sig, i,val);
    plugin_data->data_buf[plugin_data->buffer_count++] = (double)val;
    val = (val <0 ? -val : val);
    max = val > max ? val : max;
      if (plugin_data->buffer_count ==plugin_data->buffer_size){
         double pitch =  __compute_pitch( tuner );
      radspa_signal_set_const_value(pitch_sig, (int16_t)(pitch*10));
      plugin_data->buffer_count=0;
      }
   }
   if (max!=-32767){
    	radspa_signal_set_const_value(max_sig, max);
    }

};
