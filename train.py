import tensorflow as tf
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
import os
import shutil
import random

# --- Constants (Adjust these if needed) ---
IMAGE_SIZE = (224, 224)  # EfficientNetB0 input size
BATCH_SIZE = 16  # Use a smaller batch size if you have limited memory
EPOCHS = 50  # Maximum number of epochs (EarlyStopping will likely stop sooner)
DATA_DIR = "image_data_serpapi"  #  Path to your data directory
TRAIN_DIR = os.path.join(DATA_DIR, "train")
VALIDATION_DIR = os.path.join(DATA_DIR, "validation")
MODEL_SAVE_PATH = "efficientnet_phone_model.h5"  # Where to save the trained model

# --- 1. Data Splitting (Train/Validation) ---

def create_train_val_split(data_dir, train_dir, validation_dir, validation_split=0.3):
    """Splits the data into training and validation sets."""

    # Remove directories if they exist, then recreate them
    if os.path.exists(train_dir):
        shutil.rmtree(train_dir)
    if os.path.exists(validation_dir):
        shutil.rmtree(validation_dir)
    os.makedirs(train_dir)
    os.makedirs(validation_dir)

    for product_folder in os.listdir(data_dir):
        product_path = os.path.join(data_dir, product_folder)
        if not os.path.isdir(product_path):
            continue  # Skip files, only process directories

        images = [f for f in os.listdir(product_path) if os.path.isfile(os.path.join(product_path, f))]
        random.shuffle(images)  # Shuffle for random split

        # Calculate the split index
        split_index = int(len(images) * (1 - validation_split))
        train_images = images[:split_index]
        val_images = images[split_index:]

        # Create subdirectories in train and validation directories
        train_product_dir = os.path.join(train_dir, product_folder)
        val_product_dir = os.path.join(validation_dir, product_folder)
        os.makedirs(train_product_dir, exist_ok=True)  # exist_ok=True prevents errors if dir exists
        os.makedirs(val_product_dir, exist_ok=True)

        # Copy images to the correct directories
        for image in train_images:
            src = os.path.join(product_path, image)
            dst = os.path.join(train_product_dir, image)
            shutil.copy(src, dst)
        for image in val_images:
            src = os.path.join(product_path, image)
            dst = os.path.join(val_product_dir, image)
            shutil.copy(src, dst)

# --- 2. Data Generators (with Augmentation) ---

def create_data_generators(train_dir, validation_dir, image_size, batch_size):
    """Creates ImageDataGenerators for training and validation."""

    # Training data generator with augmentation
    train_datagen = ImageDataGenerator(
        rescale=1. / 255,
        rotation_range=40,  # Increased rotation range
        width_shift_range=0.3,  # Increased shift range
        height_shift_range=0.3,  # Increased shift range
        shear_range=0.3,
        zoom_range=0.3,
        horizontal_flip=True,
        vertical_flip=True,   # Add vertical flips as well
        fill_mode='nearest'
    )

    # Validation data generator (only rescaling)
    validation_datagen = ImageDataGenerator(rescale=1. / 255)

    # Create the generators
    train_generator = train_datagen.flow_from_directory(
        train_dir,
        target_size=image_size,
        batch_size=batch_size,
        class_mode='categorical'  #  We have multiple classes (phone models)
    )

    validation_generator = validation_datagen.flow_from_directory(
        validation_dir,
        target_size=image_size,
        batch_size=batch_size,
        class_mode='categorical',
        shuffle=False  # Don't shuffle validation data
    )

    return train_generator, validation_generator

# --- 3. Model Definition (EfficientNetB0) ---

def create_model(num_classes):
    """Creates the EfficientNetB0 model with custom top layers."""

    base_model = EfficientNetB0(weights='imagenet', include_top=False, input_shape=IMAGE_SIZE + (3,))
    base_model.trainable = False  # Freeze the base model's layers

    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(1024, activation='relu')(x)  # Add a dense layer
    x = Dropout(0.5)(x)  # Add dropout for regularization
    predictions = Dense(num_classes, activation='softmax')(x)  # Output layer

    model = Model(inputs=base_model.input, outputs=predictions)
    return model

# --- 4. Training Loop ---

def compile_and_train_model(model, train_generator, validation_generator, epochs, model_save_path):
    """Compiles and trains the model, using callbacks."""

    model.compile(optimizer=Adam(learning_rate=0.0001),  # Use a relatively low learning rate
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])

    # --- Callbacks ---
    # 1. ModelCheckpoint: Save the best model during training
    checkpoint = ModelCheckpoint(model_save_path, monitor='val_accuracy', save_best_only=True, mode='max', verbose=1)

    # 2. EarlyStopping: Stop training if validation loss doesn't improve
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1)

    # 3. ReduceLROnPlateau: Reduce learning rate if validation loss plateaus
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2, patience=5, min_lr=0.00001, verbose=1)

    callbacks = [checkpoint, early_stopping, reduce_lr]

    # --- Train the model ---
    history = model.fit(
        train_generator,
        steps_per_epoch=train_generator.samples // train_generator.batch_size,
        epochs=epochs,
        validation_data=validation_generator,
        validation_steps=validation_generator.samples // validation_generator.batch_size,
        callbacks=callbacks
    )
    return history



# --- Main Execution ---

if __name__ == "__main__":
    # 1. Create the training/validation split
    create_train_val_split(DATA_DIR, TRAIN_DIR, VALIDATION_DIR)

    # 2. Create data generators
    train_generator, validation_generator = create_data_generators(TRAIN_DIR, VALIDATION_DIR, IMAGE_SIZE, BATCH_SIZE)

    # 3. Get the number of classes (dynamically)
    num_classes = train_generator.num_classes

    # 4. Create the model
    model = create_model(num_classes)

    # 5. Compile and train the model
    history = compile_and_train_model(model, train_generator, validation_generator, EPOCHS, MODEL_SAVE_PATH)

    print("Training complete! Model saved to:", MODEL_SAVE_PATH)
