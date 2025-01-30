% Thermistor Calibration Script

% Given values
Rdivider = 56e3; % 56k ohms
Vin = 5.5;         % 5V input voltage

% Fixed Resistor values
Rtherm = [467.9, 149.2e3]; % Shared Rtherm values for all sensors

% Ideal Voltage given fixed resistor and voltage divider circuit.
Vout_ideal = (Rtherm ./ (Rtherm + Rdivider)) * Vin;

% Actual measured values for calibration
%            [V_470Ohm, V_150kOhm]
Vout_actual = [0.044, 3.95; % Sensor 1
               0.044, 3.94; % Sensor 2
               0.044, 3.92; % Sensor 3
               0.045, 3.93; % Sensor 4
               0.044, 3.95; % Sensor 5
               0.044, 3.92; % Sensor 6
               0.044, 3.93; % Sensor 7
               0.044, 3.93]; % Sensor 8

% Loop through each sensor for calibration
num_sensors = size(Vout_actual, 1);
coeffs = zeros(num_sensors, 2); % Store calibration coefficients for all sensors

for sensor_idx = 1:num_sensors
    % Get actual voltage values for the current sensor
    Vout_act = Vout_actual(sensor_idx, :);

    % Fit a linear model for calibration: Vout_actual = a * Vout_ideal + b
    coeffs(sensor_idx, :) = polyfit(Vout_ideal, Vout_act, 1);
    a = coeffs(sensor_idx, 1); % Slope
    b = coeffs(sensor_idx, 2); % Intercept

    fprintf('Sensor %d calibration equation: Vout_calibrated = (vout_actual - %.4f) / %.4f\n', sensor_idx, b, a);

    % Apply calibration to ideal voltages
    Vout_calibrated = (Vout_act - b) / a;

    figure();
    hold on;
    % Plot the results for the current sensor
    plot(Rtherm, Vout_ideal, 'b-', 'LineWidth', 1.5);
    plot(Rtherm, Vout_act, 'r-', 'LineWidth', 1.5, 'MarkerSize', 8);
    plot(Rtherm, Vout_calibrated, '--', 'LineWidth', 1.5);
    
    grid on;
    legend('Ideal Vout', 'Measured Vout', 'Calibrated Vout', 'Location', 'southeast');
    title(sprintf('Thermistor Calibration for Sensor %d', sensor_idx));
    xlabel('Thermistor Resistance (Ohms)');
    ylabel('Output Voltage (V)');
    hold off;
    saveas(gcf, sprintf('plots/channel%d_voltage_calibration.png', sensor_idx)); % Save as a PNG file
end


