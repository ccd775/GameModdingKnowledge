#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "HLKToolsLibrary.generated.h"

class UAnimBlueprint;
class USkeleton;

UCLASS()
class UHLKToolsLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	// Creates (and compiles) an anim blueprint at PackagePath (e.g. /Game/Karin/ABP_Karin_F_Body) for Skeleton:
	//   source -> LocalToComponent -> AnimDynamics x N -> ComponentToLocal -> Output
	// Source is CopyPoseFromMesh configured from CopyPoseJson (FAnimNode_CopyPoseFromMesh fields), or the
	// post-process Input Pose when CopyPoseJson is empty. DynamicsJson is a JSON array of FAnimNode_AnimDynamics
	// objects (UPROPERTY names; enums by name; bones as {"BoneName": "..."}). Returns null on failure; the caller saves.
	UFUNCTION(BlueprintCallable, Category = "HLK")
	static UAnimBlueprint* CreateDynamicsAnimBlueprint(const FString& PackagePath, USkeleton* Skeleton, const FString& CopyPoseJson, const FString& DynamicsJson);
};
